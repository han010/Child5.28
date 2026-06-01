#!/usr/bin/env python3
"""
融合odom的GPS多点轨迹导航控制节点

导航策略：
1. GPS坐标 -> 转换为局部坐标系下的目标点 (米)
2. 使用odom的高精度位姿进行控制
3. odom融合了IMU和轮速计，精度更高、更新频率稳定
4. 支持多点轨迹自动执行

坐标系说明：
- odom坐标系：机器人启动时的位置为原点，启动时的朝向为x轴
- 目标点：在odom坐标系下表示 (meters)

使用方式：
1. 单点模式：通过参数设置单个目标点
2. 多点模式：通过参数设置waypoint_list，按顺序执行
3. 循环模式：设置loop=true，执行完所有点后重新开始
"""

import math
import json
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from std_srvs.srv import Trigger, SetBool


class GPSWaypointNavigatorOdom(Node):
    def __init__(self):
        super().__init__('gps_waypoint_nav_odom')

        # 声明参数
        self.declare_parameter('target_latitude', 30.2551044)
        self.declare_parameter('target_longitude', 120.294113)
        self.declare_parameter('waypoint_list', '[]')  # JSON格式的航点列表
        self.declare_parameter('loop_waypoints', False)  # 是否循环执行
        self.declare_parameter('tolerance', 1.0)  # 到达容差(米)
        self.declare_parameter('linear_speed', 0.5)  # 前进速度 m/s
        self.declare_parameter('angular_speed', 0.3)  # 转向速度 rad/s
        self.declare_parameter('angle_tolerance', 0.1)  # 角度容差 rad (~5度)
        self.declare_parameter('use_slow_approach', True)  # 接近目标时减速
        self.declare_parameter('slow_distance', 2.0)  # 开始减速的距离(米)
        self.declare_parameter('slow_speed_ratio', 0.3)  # 减速比例
        self.declare_parameter('wait_at_waypoint', 0.0)  # 到达航点后等待时间(秒)

        # 获取参数
        self.target_lat = self.get_parameter('target_latitude').value
        self.target_lon = self.get_parameter('target_longitude').value
        waypoint_list_json = self.get_parameter('waypoint_list').value
        self.loop_waypoints = self.get_parameter('loop_waypoints').value
        self.tolerance = self.get_parameter('tolerance').value
        self.linear_speed = self.get_parameter('linear_speed').value
        self.angular_speed = self.get_parameter('angular_speed').value
        self.angle_tolerance = self.get_parameter('angle_tolerance').value
        self.use_slow_approach = self.get_parameter('use_slow_approach').value
        self.slow_distance = self.get_parameter('slow_distance').value
        self.slow_speed_ratio = self.get_parameter('slow_speed_ratio').value
        self.wait_at_waypoint = self.get_parameter('wait_at_waypoint').value

        # 解析航点列表
        try:
            self.waypoints = json.loads(waypoint_list_json)
            if not isinstance(self.waypoints, list):
                self.waypoints = []
        except json.JSONDecodeError:
            self.waypoints = []

        # 如果有航点列表，使用航点列表的第一个点作为初始目标
        if self.waypoints:
            self.target_lat = self.waypoints[0].get('latitude', self.target_lat)
            self.target_lon = self.waypoints[0].get('longitude', self.target_lon)

        # GPS坐标系初始化状态
        self.gps_origin_lat = None
        self.gps_origin_lon = None
        self.gps_init_done = False

        # 目标点在odom坐标系中的位置
        self.target_x = None
        self.target_y = None

        # 机器人当前位姿 (odom坐标系)
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_yaw = 0.0
        self.odom_ready = False

        # 导航状态
        self.goal_reached = False
        self.nav_active = False
        self.current_waypoint_index = 0
        self.waypoints_odom = []  # 存储转换后的odom坐标系航点
        self.mission_complete = False
        self.wait_start_time = None
        self.is_waiting = False

        # 地球半径 (米)
        self.earth_radius = 6378137.0

        # 发布器
        self.cmd_vel_pub = self.create_publisher(Twist, '/revo/cmd_vel', 10)
        self.status_pub = self.create_publisher(String, '/nav_status', 10)

        # 订阅器
        self.gps_sub = self.create_subscription(
            NavSatFix,
            '/gps/fix',
            self.gps_callback,
            10
        )

        self.odom_sub = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10
        )

        # 服务
        self.create_service(Trigger, 'start_mission', self.start_mission_callback)
        self.create_service(Trigger, 'pause_mission', self.pause_mission_callback)
        self.create_service(Trigger, 'resume_mission', self.resume_mission_callback)
        self.create_service(Trigger, 'reset_mission', self.reset_mission_callback)
        self.create_service(SetBool, 'set_loop_mode', self.set_loop_mode_callback)

        # 控制定时器 (20Hz)
        self.create_timer(0.05, self.control_loop)

        # 日志
        self._log_startup_info()

    def _log_startup_info(self):
        """输出启动信息"""
        info = (
            f'GPS Waypoint Navigator (Odom Fusion) started!\n'
            f'  Target GPS: ({self.target_lat:.8f}, {self.target_lon:.8f})\n'
            f'  Tolerance: {self.tolerance}m\n'
            f'  Speed: {self.linear_speed}m/s\n'
        )

        if self.waypoints:
            info += f'\n  Waypoints: {len(self.waypoints)} points loaded\n'
            info += f'  Loop mode: {"Enabled" if self.loop_waypoints else "Disabled"}\n'
            for i, wp in enumerate(self.waypoints):
                info += f'    [{i+1}] ({wp["latitude"]:.8f}, {wp["longitude"]:.8f})\n'

        info += '  Waiting for GPS to initialize odom origin...'
        self.get_logger().info(info)

    def gps_callback(self, msg: NavSatFix):
        """
        GPS回调 - 仅用于初始化odom原点
        第一次收到有效GPS时，将其作为odom坐标系的原点 (0,0)
        """
        if msg.status.status < 0:
            return  # 无效定位

        if self.gps_init_done:
            return  # 已经初始化过了

        # 记录GPS原点
        self.gps_origin_lat = msg.latitude
        self.gps_origin_lon = msg.longitude
        self.gps_init_done = True

        # 如果有航点列表，转换所有航点到odom坐标系
        if self.waypoints:
            self.waypoints_odom = []
            for wp in self.waypoints:
                x, y = self._lonlat_to_meters(
                    wp['longitude'], wp['latitude'],
                    self.gps_origin_lon, self.gps_origin_lat
                )
                self.waypoints_odom.append({'x': x, 'y': y})

            self.target_x = self.waypoints_odom[0]['x']
            self.target_y = self.waypoints_odom[0]['y']
        else:
            # 单点模式
            self.target_x, self.target_y = self._lonlat_to_meters(
                self.target_lon, self.target_lat,
                self.gps_origin_lon, self.gps_origin_lat
            )

        self.nav_active = True
        self._publish_status('GPS initialized', 'active')
        self.get_logger().info(
            f'GPS origin initialized!\n'
            f'  Origin: ({self.gps_origin_lat:.8f}, {self.gps_origin_lon:.8f})\n'
            f'  Current target in odom: x={self.target_x:.2f}m, y={self.target_y:.2f}m'
        )

    def odom_callback(self, msg: Odometry):
        """里程计回调 - 更新机器人位姿"""
        # 提取位置
        self.robot_x = msg.pose.pose.position.x
        self.robot_y = msg.pose.pose.position.y

        # 提取航向角 (从四元数)
        q = msg.pose.pose.orientation
        self.robot_yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        )

        self.odom_ready = True

    def _lonlat_to_meters(self, lon: float, lat: float, lon0: float, lat0: float):
        """
        将经纬度转换为相对于原点的米制坐标
        返回: (x, y) 单位: 米
        """
        deg2rad = math.pi / 180.0
        lat0_rad = lat0 * deg2rad

        # x方向: 经度差 * 地球半径 * cos(纬度)
        dx = (lon - lon0) * deg2rad * self.earth_radius * math.cos(lat0_rad)
        # y方向: 纬度差 * 地球半径
        dy = (lat - lat0) * deg2rad * self.earth_radius

        return dx, dy

    def normalize_angle(self, angle):
        """将角度规范化到[-pi, pi]"""
        return math.atan2(math.sin(angle), math.cos(angle))

    def control_loop(self):
        """主控制循环"""
        cmd = Twist()

        # 检查系统是否就绪
        if not self.odom_ready or not self.nav_active:
            return

        # 检查任务是否完成
        if self.mission_complete:
            return

        # 检查是否在等待
        if self.is_waiting:
            if self.get_clock().now().nanoseconds * 1e-9 - self.wait_start_time >= self.wait_at_waypoint:
                self.is_waiting = False
                self.wait_start_time = None
                self._proceed_to_next_waypoint()
            return

        # 计算到目标的距离（在odom坐标系中）
        dx = self.target_x - self.robot_x
        dy = self.target_y - self.robot_y
        distance = math.sqrt(dx * dx + dy * dy)

        # 检查是否到达当前航点
        if distance < self.tolerance:
            if self.wait_at_waypoint > 0:
                # 开始等待
                self.is_waiting = True
                self.wait_start_time = self.get_clock().now().nanoseconds * 1e-9
                cmd.linear.x = 0.0
                cmd.angular.z = 0.0
                self.cmd_vel_pub.publish(cmd)
                self.get_logger().info(
                    f'Waypoint {self.current_waypoint_index + 1}/{len(self.waypoints_odom)} reached! '
                    f'Waiting {self.wait_at_waypoint}s...'
                )
                return
            else:
                # 直接进入下一个航点
                self._proceed_to_next_waypoint()
                return

        # 计算目标方位角
        target_yaw = math.atan2(dy, dx)

        # 计算角度误差
        angle_error = self.normalize_angle(target_yaw - self.robot_yaw)

        # 根据距离调整线速度（接近目标时减速）
        linear_speed = self.linear_speed
        if self.use_slow_approach and distance < self.slow_distance:
            # 线性减速
            ratio = self.slow_speed_ratio + (1.0 - self.slow_speed_ratio) * (distance / self.slow_distance)
            linear_speed *= ratio

        # 打印调试信息
        wp_info = f'WP: {self.current_waypoint_index + 1}' if self.waypoints_odom else 'WP: Single'
        self.get_logger().info(
            f'{wp_info} | Dist: {distance:.2f}m | '
            f'Robot: ({self.robot_x:.2f}, {self.robot_y:.2f}) | '
            f'Yaw: {math.degrees(self.robot_yaw):.1f}° | '
            f'Err: {math.degrees(angle_error):.1f}°',
            throttle_duration_sec=0.5
        )

        # 控制策略：极坐标控制
        if abs(angle_error) > self.angle_tolerance:
            # 纯转向阶段
            cmd.angular.z = self.angular_speed if angle_error > 0 else -self.angular_speed
            cmd.linear.x = 0.0
        else:
            # 前进阶段（带转向修正）
            cmd.linear.x = linear_speed
            cmd.angular.z = 0.5 * self.angular_speed if angle_error > 0 else -0.5 * self.angular_speed

        self.cmd_vel_pub.publish(cmd)

    def _proceed_to_next_waypoint(self):
        """前进到下一个航点"""
        if self.waypoints_odom:
            self.current_waypoint_index += 1

            # 检查是否完成所有航点
            if self.current_waypoint_index >= len(self.waypoints_odom):
                if self.loop_waypoints:
                    # 循环模式：重新开始
                    self.current_waypoint_index = 0
                    self.get_logger().info('All waypoints completed! Looping back to start...')
                else:
                    # 任务完成
                    self.mission_complete = True
                    cmd = Twist()
                    cmd.linear.x = 0.0
                    cmd.angular.z = 0.0
                    self.cmd_vel_pub.publish(cmd)
                    self._publish_status('Mission complete!', 'complete')
                    self.get_logger().info(
                        f'Mission complete! All {len(self.waypoints_odom)} waypoints reached.'
                    )
                    return

            # 设置新目标
            self.target_x = self.waypoints_odom[self.current_waypoint_index]['x']
            self.target_y = self.waypoints_odom[self.current_waypoint_index]['y']

            wp_lat = self.waypoints[self.current_waypoint_index]['latitude']
            wp_lon = self.waypoints[self.current_waypoint_index]['longitude']

            self.get_logger().info(
                f'Proceeding to waypoint {self.current_waypoint_index + 1}/{len(self.waypoints_odom)}\n'
                f'  GPS: ({wp_lat:.8f}, {wp_lon:.8f})\n'
                f'  Odom: x={self.target_x:.2f}m, y={self.target_y:.2f}m'
            )
        else:
            # 单点模式：任务完成
            self.mission_complete = True
            cmd = Twist()
            cmd.linear.x = 0.0
            cmd.angular.z = 0.0
            self.cmd_vel_pub.publish(cmd)
            self._publish_status('Goal reached!', 'complete')
            self.get_logger().info('Goal reached! Mission complete.')

    def _publish_status(self, message: str, status_type: str):
        """发布导航状态"""
        msg = String()
        msg.data = json.dumps({
            'status': status_type,
            'message': message,
            'current_waypoint': self.current_waypoint_index + 1,
            'total_waypoints': len(self.waypoints_odom) if self.waypoints_odom else 1,
            'position': {'x': self.robot_x, 'y': self.robot_y, 'yaw': self.robot_yaw}
        })
        self.status_pub.publish(msg)

    # ==================== 服务回调 ====================

    def start_mission_callback(self, request, response):
        """开始任务服务"""
        if self.mission_complete:
            self.mission_complete = False
            self.current_waypoint_index = 0
            if self.waypoints_odom:
                self.target_x = self.waypoints_odom[0]['x']
                self.target_y = self.waypoints_odom[0]['y']
            self.get_logger().info('Mission restarted!')
        response.success = True
        response.message = 'Mission started/restarted'
        return response

    def pause_mission_callback(self, request, response):
        """暂停任务服务"""
        self.nav_active = False
        cmd = Twist()
        cmd.linear.x = 0.0
        cmd.angular.z = 0.0
        self.cmd_vel_pub.publish(cmd)
        self._publish_status('Mission paused', 'paused')
        self.get_logger().info('Mission paused')
        response.success = True
        response.message = 'Mission paused'
        return response

    def resume_mission_callback(self, request, response):
        """恢复任务服务"""
        self.nav_active = True
        self._publish_status('Mission resumed', 'active')
        self.get_logger().info('Mission resumed')
        response.success = True
        response.message = 'Mission resumed'
        return response

    def reset_mission_callback(self, request, response):
        """重置任务服务"""
        self.current_waypoint_index = 0
        self.mission_complete = False
        self.is_waiting = False
        if self.waypoints_odom:
            self.target_x = self.waypoints_odom[0]['x']
            self.target_y = self.waypoints_odom[0]['y']
        self.get_logger().info('Mission reset to start')
        response.success = True
        response.message = 'Mission reset'
        return response

    def set_loop_mode_callback(self, request, response):
        """设置循环模式服务"""
        self.loop_waypoints = request.data
        self.get_logger().info(f'Loop mode: {"enabled" if self.loop_waypoints else "disabled"}')
        response.success = True
        response.message = f'Loop mode set to {self.loop_waypoints}'
        return response


def main(args=None):
    rclpy.init(args=args)

    node = GPSWaypointNavigatorOdom()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # 停止机器人
        cmd = Twist()
        node.cmd_vel_pub.publish(cmd)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
