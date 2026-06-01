#!/usr/bin/env python3
import math
import threading
import time
import atexit

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Vector3
from revo_msgs.msg import PoseState as PoseStateMsg, SystemStatus as SystemStatusMsg
from std_srvs.srv import Trigger
import tf2_ros


class RevoOdomNode(Node):
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        # 使用匿名节点名确保唯一性
        super().__init__('revo_odom_node')

        # 注册退出时清理
        atexit.register(self._cleanup_on_exit)

        # 检查是否已有其他odom发布者
        self._check_existing_odom_publishers()
        # parameters
        self.declare_parameter('odom_frame_id', 'odom')
        self.declare_parameter('base_frame_id', 'base_link')
        self.declare_parameter('odom_publish_rate_hz', 20)
        self.declare_parameter('odom_smoothing_alpha', 0.5)
        self.declare_parameter('odom_deadzone_linear', 0.005)
        self.declare_parameter('odom_deadzone_angular', 0.002)
        self.declare_parameter('odom_max_dt', 0.5)
        self.declare_parameter('gnss_good_window', 3)
        self.declare_parameter('gnss_align_steps', 10)
        self.declare_parameter('gnss_align_max_jump', 2.0)

        self.odom_frame_id = self.get_parameter('odom_frame_id').value
        self.base_frame_id = self.get_parameter('base_frame_id').value
        self.odom_rate = float(self.get_parameter('odom_publish_rate_hz').value)

        # odom state
        self._odom_x = 0.0
        self._odom_y = 0.0
        self._odom_yaw = 0.0
        self._odom_v_prev = 0.0
        self._odom_omega_prev = 0.0
        self._odom_smoothing_alpha = float(self.get_parameter('odom_smoothing_alpha').value)
        self._odom_deadzone_linear = float(self.get_parameter('odom_deadzone_linear').value)
        self._odom_deadzone_angular = float(self.get_parameter('odom_deadzone_angular').value)
        self._odom_max_dt = float(self.get_parameter('odom_max_dt').value)
        self._last_odom_time = self.get_clock().now()
        # 初始yaw偏移量：用于将odom坐标系的x轴与机器人启动时的朝向对齐
        self._initial_yaw_offset = None
        self._yaw_initialized = False

        # GNSS init
        self._gnss_good_count = 0
        self._gnss_good_window = int(self.get_parameter('gnss_good_window').value)
        self._gnss_align_steps = int(self.get_parameter('gnss_align_steps').value)
        self._gnss_align_max_jump = float(self.get_parameter('gnss_align_max_jump').value)
        self._gnss_init_done = False
        self._gnss_origin_lon = None
        self._gnss_origin_lat = None
        self._gnss_align_remaining = 0
        self._gnss_align_dx_step = 0.0
        self._gnss_align_dy_step = 0.0
        self._earth_radius = 6378137.0

        # publishers / subscribers
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self._initial_yaw_pub = self.create_publisher(Vector3, '/odom/initial_yaw_offset', 10)
        try:
            self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        except Exception:
            self.tf_broadcaster = None

        self._pose = None
        self._system = None
        self._cache_lock = threading.Lock()

        self.create_subscription(PoseStateMsg, 'revo/pose', self._on_pose, 10)
        self.create_subscription(SystemStatusMsg, 'revo/system_status', self._on_system, 10)

        # 创建重置服务
        self.create_service(Trigger, 'reset_odom', self._reset_odom_callback)

        # 保存timer引用用于清理
        self._timer = None
        self._yaw_timer = None
        if self.odom_rate > 0:
            self._timer = self.create_timer(1.0 / self.odom_rate, self._timer_cb)
        else:
            self.get_logger().warn(f'odom_rate is {self.odom_rate}, timer NOT created!')

        # 定期发布initial_yaw_offset，供GPS目标工具使用
        self._yaw_timer = self.create_timer(1.0, self._publish_initial_yaw)

    def _publish_initial_yaw(self):
        """定期发布initial_yaw_offset，供GPS目标工具使用"""
        if self._yaw_initialized and self._initial_yaw_offset is not None:
            offset_msg = Vector3()
            offset_msg.x = self._initial_yaw_offset
            self._initial_yaw_pub.publish(offset_msg)

    def _on_pose(self, msg: PoseStateMsg):
        with self._cache_lock:
            self._pose = msg

    def _on_system(self, msg: SystemStatusMsg):
        with self._cache_lock:
            self._system = msg

    def _check_existing_odom_publishers(self):
        """检查是否已有其他odom发布者在运行"""
        try:
            # 等待一小段时间让DDS发现其他节点
            import asyncio
            import concurrent.futures

            def get_publishers():
                # 创建一个临时节点来查询
                rclpy.init(args=None)
                tmp_node = rclpy.create_node('tmp_odom_checker')
                publishers_info = tmp_node.get_publishers_info_by_topic('odom')
                tmp_node.destroy_node()
                rclpy.shutdown()
                return publishers_info

            # 在线程中执行，避免阻塞初始化
            try:
                # 使用timeout避免长时间等待
                import subprocess
                result = subprocess.run(
                    ['ros2', 'topic', 'info', '/odom', '--once'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'Publisher count:' in line:
                            count = int(line.split(':')[1].strip())
                            if count > 0:
                                self.get_logger().warn(
                                    f'检测到已有 {count} 个 /odom 发布者在运行！'
                                )
                                self.get_logger().warn(
                                    '这可能导致里程计数据不一致。建议先关闭其他odom节点。'
                                )
            except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
                pass
        except Exception as e:
            # 检查失败不影响启动
            self.get_logger().debug(f'检查现有发布者失败: {e}')

    def _cleanup_on_exit(self):
        """退出时清理资源"""
        try:
            self.get_logger().info('正在清理odom发布者...')
        except:
            pass

    def destroy_node(self):
        """重写destroy_node确保正确清理所有资源"""
        self.get_logger().info('销毁odom节点...')

        # 停止发布
        try:
            if hasattr(self, 'odom_pub') and self.odom_pub:
                self.odom_pub.unregister()
                self.get_logger().info('已注销 /odom 发布者')
        except Exception as e:
            self.get_logger().debug(f'注销发布者时出错: {e}')

        # 销毁TF广播器
        try:
            if hasattr(self, 'tf_broadcaster') and self.tf_broadcaster:
                del self.tf_broadcaster
        except Exception as e:
            self.get_logger().debug(f'清理TF广播器时出错: {e}')

        # 清理定时器
        try:
            self.destroy_timer(self._timer)
        except:
            pass
        try:
            self.destroy_timer(self._yaw_timer)
        except:
            pass

        # 调用父类清理
        try:
            super().destroy_node()
        except Exception as e:
            self.get_logger().debug(f'父类destroy_node时出错: {e}')

        self.get_logger().info('odom节点已销毁')

    def _reset_odom_callback(self, request, response):
        """重置里程计位置为原点"""
        with self._cache_lock:
            self._odom_x = 0.0
            self._odom_y = 0.0
            self._odom_yaw = 0.0
            self._odom_v_prev = 0.0
            self._odom_omega_prev = 0.0
            # 重置初始yaw偏移量，下次收到pose数据时会重新记录
            self._initial_yaw_offset = None
            self._yaw_initialized = False

        response.success = True
        response.message = '里程计已重置为原点 (0, 0, 0)'
        self.get_logger().info('里程计已重置（包括yaw偏移量）')
        return response

    def _bit(self, status: int, n: int) -> bool:
        return bool(status & (1 << n))

    def _is_gnss_sample_good(self, status: int) -> bool:
        if self._bit(status, 0):
            return False
        if self._bit(status, 9):
            return False
        if not self._bit(status, 4):
            if self._bit(status, 3) or self._bit(status, 6) or self._bit(status, 8):
                return False
            return True
        if self._bit(status, 5):
            return False
        if self._bit(status, 10):
            return False
        if self._bit(status, 11):
            return False
        if self._bit(status, 13) or self._bit(status, 2):
            return False
        return True

    def _lonlat_to_meters(self, lon: float, lat: float, lon0: float, lat0: float):
        deg2rad = math.pi / 180.0
        lat0_rad = lat0 * deg2rad
        dx = (lon - lon0) * deg2rad * self._earth_radius * math.cos(lat0_rad)
        dy = (lat - lat0) * deg2rad * self._earth_radius
        return dx, dy

    def _timer_cb(self):
        now = self.get_clock().now()
        dt = (now - self._last_odom_time).nanoseconds * 1e-9
        if dt <= 0:
            self._last_odom_time = now
            return
        if dt > self._odom_max_dt:
            self._last_odom_time = now
            return
        with self._cache_lock:
            pose = self._pose
            system = self._system
        if pose is None:
            self._last_odom_time = now
            return

        # Try GNSS-based initialization
        try:
            if not self._gnss_init_done:
                status = int(getattr(system, 'positioning_status', 0)) if system is not None else 0
                lon = float(pose.longitude) / 1e7 if hasattr(pose, 'longitude') else 0.0
                lat = float(pose.latitude) / 1e7 if hasattr(pose, 'latitude') else 0.0
                if lon and lat and not (lon == 0.0 and lat == 0.0):
                    if self._is_gnss_sample_good(status):
                        self._gnss_good_count += 1
                    else:
                        self._gnss_good_count = 0
                    if self._gnss_good_count >= self._gnss_good_window:
                        self._gnss_origin_lon = lon
                        self._gnss_origin_lat = lat
                        self._gnss_init_done = True
                else:
                    self._gnss_good_count = 0
        except Exception:
            pass

        # 参考官方 path_tracking.py 实现：
        # 1. 角度直接使用 IMU 的 yaw（更准确，不受轮子打滑影响）
        # 2. 位置使用轮速计线速度（不受GPS丢失影响）+ IMU yaw 积分
        try:
            # 从 IMU 直接获取航向角（单位：1/1000 弧度 -> 弧度）
            # Revo IMU 使用右手系（顺时针为正），ROS 使用左手系（逆时针为正）
            # 测试确认：左转90度后 raw yaw 减小约90度，需要取反以符合 ROS REP-103 标准
            imu_yaw = -float(pose.yaw) / 1000.0

            # 初始化yaw偏移量：第一次收到有效yaw时记录，确保odom启动时yaw=0
            if not self._yaw_initialized:
                self._initial_yaw_offset = imu_yaw
                self._yaw_initialized = True
                self.get_logger().info(f'初始化yaw偏移量: {self._initial_yaw_offset:.3f} rad '
                                      f'({math.degrees(self._initial_yaw_offset):.1f}°)')

            # 计算odom的yaw：减去初始偏移量，使得启动时odom的yaw=0
            # 这样odom坐标系的x轴就与机器人启动时的朝向对齐
            self._odom_yaw = imu_yaw - self._initial_yaw_offset

            # 规范化yaw到[-pi, pi]范围
            while self._odom_yaw > math.pi:
                self._odom_yaw -= 2.0 * math.pi
            while self._odom_yaw < -math.pi:
                self._odom_yaw += 2.0 * math.pi

            # 使用轮速计线速度（单位：1/100 m/s -> m/s）
            # 轮速计不受GPS丢失影响，比融合速度更可靠
            v = float(pose.wheel_linear_velocity) / 100.0
            # 轮角速度也需要取反以符合 ROS 坐标系约定
            wheel_omega = -float(pose.wheel_angular_velocity) / 1000.0

            # deadzone
            if abs(v) < self._odom_deadzone_linear:
                v = 0.0

            # 线速度平滑
            alpha = self._odom_smoothing_alpha
            v = alpha * self._odom_v_prev + (1.0 - alpha) * v
            self._odom_v_prev = v

            # 位置积分：使用轮速计线速度 + IMU yaw
            if abs(wheel_omega) < 0.001:
                # 直线运动
                self._odom_x += v * math.cos(self._odom_yaw) * dt
                self._odom_y += v * math.sin(self._odom_yaw) * dt
            else:
                # 圆弧运动
                R = v / wheel_omega
                dtheta = wheel_omega * dt
                self._odom_x += R * (math.sin(self._odom_yaw + dtheta) - math.sin(self._odom_yaw))
                self._odom_y += R * (-math.cos(self._odom_yaw + dtheta) + math.cos(self._odom_yaw))

            # build odom msg
            odom = Odometry()
            odom.header.stamp = now.to_msg()
            odom.header.frame_id = self.odom_frame_id
            odom.child_frame_id = self.base_frame_id
            odom.pose.pose.position.x = round(self._odom_x, 2)
            odom.pose.pose.position.y = round(self._odom_y, 2)

            # 使用 IMU 的 yaw 角
            pub_yaw = self._odom_yaw
            qz = math.sin(pub_yaw / 2.0)
            qw = math.cos(pub_yaw / 2.0)
            odom.pose.pose.orientation.x = 0.0
            odom.pose.pose.orientation.y = 0.0
            odom.pose.pose.orientation.z = qz
            odom.pose.pose.orientation.w = qw

            odom.twist.twist.linear.x = round(v, 2)
            # twist.angular.z 使用轮角速度（瞬时值）
            omega_smoothed = alpha * self._odom_omega_prev + (1.0 - alpha) * wheel_omega
            self._odom_omega_prev = omega_smoothed
            odom.twist.twist.angular.z = round(omega_smoothed, 3)

            cov_pose = [
                1e-4, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 1e-4, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 1e6, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 1e6, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 1e6, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 1e-4,
            ]
            odom.pose.covariance = [float(x) for x in cov_pose]
            cov_twist = [
                4e-4, 0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 1e6, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 1e6, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 1e6, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 1e6, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, 1e-4,
            ]
            odom.twist.covariance = [float(x) for x in cov_twist]

            self.odom_pub.publish(odom)

            if self.tf_broadcaster is not None:
                t = TransformStamped()
                t.header.stamp = odom.header.stamp
                t.header.frame_id = self.odom_frame_id
                t.child_frame_id = self.base_frame_id
                t.transform.translation.x = round(self._odom_x, 2)
                t.transform.translation.y = round(self._odom_y, 2)
                t.transform.translation.z = 0.0
                t.transform.rotation = odom.pose.pose.orientation
                self.tf_broadcaster.sendTransform(t)

        except Exception as e:
            self.get_logger().error(f'计算/发布 odom 失败: {e}')

        finally:
            self._last_odom_time = now


def main(args=None):
    rclpy.init(args=args)
    node = RevoOdomNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
