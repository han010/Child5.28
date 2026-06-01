#!/usr/bin/env python3
"""
ROS2 节点：Revo SDK 数据桥接节点

功能：
- 将 SDK 的位姿、系统状态、电池数据发布到 ROS 话题（JSON 字符串）
- 订阅 `revo/cmd_vel`（geometry_msgs/Twist）并将控制命令发送到 SDK

注意：为了兼容原有 SDK 的数值尺度，线速度使用 m/s * 100 转换（例如 0.5 m/s -> 50），角速度使用 rad/s * 1000 转换（例如 0.3 rad/s -> 300）。
"""
import time
import threading
import json
import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Imu
from revo_msgs.msg import PoseState as PoseStateMsg, SystemStatus as SystemStatusMsg, BatteryStatus as BatteryStatusMsg


from xa_revosdk_ugv import RevoSDK, PoseData, BatteryData, SystemStatus


class RevoBridgeNode(Node):
    def __init__(self):
        super().__init__('revo_bridge_node')
        self.declare_parameter('host', '192.168.234.1')
        self.declare_parameter('client_name', 'RevoBridge')
        self.declare_parameter('yaw_offset_deg', 0.0)

        self.host = self.get_parameter('host').get_parameter_value().string_value
        self.client_name = self.get_parameter('client_name').get_parameter_value().string_value
        self._yaw_offset_rad = math.radians(
            float(self.get_parameter('yaw_offset_deg').value)
        )

        # publishers
        self.pose_pub = self.create_publisher(PoseStateMsg, 'revo/pose', 10)
        self.system_pub = self.create_publisher(SystemStatusMsg, 'revo/system_status', 10)
        self.battery_pub = self.create_publisher(BatteryStatusMsg, 'revo/battery', 10)
        self.imu_pub = self.create_publisher(Imu, 'revo/imu', 10)

        # subscriber for control commands
        self.create_subscription(Twist, 'revo/cmd_vel', self.on_control_cmd, 10)

        # SDK
        self.sdk = RevoSDK()
        self._state_lock = threading.Lock()
        self._running = False

        # cached last data
        self._last_pose = None
        self._last_system = None
        self._last_battery = None
        self._cache_lock = threading.Lock()

        # load config file (package relative)
        import os
        import json
        from pathlib import Path

        default_cfg = {
            'pose_publish_rate_hz': 10,
            'system_publish_rate_hz': 1,
            'battery_publish_rate_hz': 1,
            # `linear_scale` / `angular_scale` are MAX speeds (limits),
            # in physical units when `cmd_vel_in_physical_units` is true:
            #  - linear_scale: max linear speed in m/s
            #  - angular_scale: max angular speed in rad/s
            'linear_scale': 2.0,
            'angular_scale': 2.0,
        }

        try:
            pkg_dir = Path(__file__).resolve().parent.parent
            cfg_path = pkg_dir / 'config' / 'revo_bridge_config.json'
            if cfg_path.exists():
                with open(cfg_path, 'r') as f:
                    cfg = json.load(f)
            else:
                cfg = default_cfg
        except Exception:
            cfg = default_cfg

        self.pose_rate = float(cfg.get('pose_publish_rate_hz', 10))
        self.system_rate = float(cfg.get('system_publish_rate_hz', 1))
        self.battery_rate = float(cfg.get('battery_publish_rate_hz', 1))
        self.linear_scale = float(cfg.get('linear_scale', 1.0))
        self.angular_scale = float(cfg.get('angular_scale', 1.0))
        # command units and SDK multipliers
        self.cmd_vel_in_physical = bool(cfg.get('cmd_vel_in_physical_units', True))
        self.sdk_linear_multiplier = float(cfg.get('sdk_linear_multiplier', 100))
        self.sdk_angular_multiplier = float(cfg.get('sdk_angular_multiplier', 1000))
        self.imu_frame_id = str(cfg.get('imu_frame_id', 'base_link'))

        # timers for periodic publishing
        if self.pose_rate > 0:
            self.create_timer(1.0 / self.pose_rate, self._publish_pose_timer)
        if self.system_rate > 0:
            self.create_timer(1.0 / self.system_rate, self._publish_system_timer)
        if self.battery_rate > 0:
            self.create_timer(1.0 / self.battery_rate, self._publish_battery_timer)

        # --- odometry (moved to separate node) ---
        # 里程计计算/发布已拆分为独立节点 revo_odom_node.py。
        # keyboard_node 仅负责将 SDK 的原始数据发布为 revo_msgs，并接收 cmd_vel。
        # self.odom_frame_id = str(cfg.get('odom_frame_id', 'odom'))
        # self.base_frame_id = str(cfg.get('base_frame_id', 'base_link'))
        # self.odom_rate = float(cfg.get('odom_publish_rate_hz', 10))
        # # odom state
        # self._odom_x = 0.0
        # self._odom_y = 0.0
        # self._odom_yaw = 0.0
        # # previous integrated velocities for smoothing
        # self._odom_v_prev = 0.0
        # self._odom_omega_prev = 0.0
        # # odom tuning params
        # self._odom_smoothing_alpha = float(cfg.get('odom_smoothing_alpha', 0.5))
        # self._odom_deadzone_linear = float(cfg.get('odom_deadzone_linear', 0.005))
        # self._odom_deadzone_angular = float(cfg.get('odom_deadzone_angular', 0.002))
        # self._odom_max_dt = float(cfg.get('odom_max_dt', 0.5))
        # # yaw smoothing via sine/cos low-pass to avoid wrap-around jumps
        # self._odom_yaw_s_prev = 0.0
        # self._odom_yaw_c_prev = 1.0
        # self._odom_yaw_alpha = self._odom_smoothing_alpha
        # self._last_odom_time = self.get_clock().now()
        # # GNSS init state
        # self._gnss_good_count = 0
        # self._gnss_good_window = int(cfg.get('gnss_good_window', 3))
        # self._gnss_align_steps = int(cfg.get('gnss_align_steps', 10))
        # self._gnss_align_max_jump = float(cfg.get('gnss_align_max_jump', 2.0))
        # self._gnss_init_done = False
        # self._gnss_origin_lon = None
        # self._gnss_origin_lat = None
        # # alignment smoothing state
        # self._gnss_align_remaining = 0
        # self._gnss_align_dx_step = 0.0
        # self._gnss_align_dy_step = 0.0
        # # Earth radius for ENU approximation
        # self._earth_radius = 6378137.0
        # self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        # try:
        #     self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        # except Exception:
        #     self.tf_broadcaster = None
        #     self.get_logger().warn('tf2_ros.TransformBroadcaster not available; skipping tf publish')
        # if self.odom_rate > 0:
        #     self.create_timer(1.0 / self.odom_rate, self._publish_odom_timer)

        # connect and subscribe
        if not self._initialize_sdk():
            self.get_logger().error('初始化 SDK 失败，节点退出')
            raise RuntimeError('SDK initialize failed')

        # keep running flag
        with self._state_lock:
            self._running = True

    def _initialize_sdk(self) -> bool:
        self.get_logger().info(f"{self.client_name} 正在连接到: {self.host}:10151")
        self.sdk.set_disconnect_callback(self._on_disconnected)
        if not self.sdk.connect(self.host):
            self.get_logger().error('连接 SDK 失败')
            return False
        if not self.sdk.register(self.client_name):
            self.get_logger().error('注册 SDK 失败')
            return False

        # 订阅 SDK 推送
        self.sdk.subscribe_pose(True, self._on_pose_data)
        self.sdk.subscribe_battery(True, self._on_battery_data)
        self.sdk.subscribe_system_status(True, self._on_system_status_data)

        # 尝试获取控制权（不是必须，但保留与原逻辑一致）
        try:
            self.sdk.acquire_control()
        except Exception:
            pass

        time.sleep(0.1)
        return True

    def _on_disconnected(self, reason: str):
        self.get_logger().warn(f'Revo SDK disconnected: {reason}')
        with self._state_lock:
            self._running = False

    def _on_pose_data(self, data: PoseData):
        # cache the latest pose; periodic timer publishes
        with self._cache_lock:
            self._last_pose = data

    def _on_battery_data(self, data: BatteryData):
        with self._cache_lock:
            self._last_battery = data

    def _on_system_status_data(self, data: SystemStatus):
        with self._cache_lock:
            self._last_system = data

    # timer callbacks publish cached data at configured rates
    def _publish_pose_timer(self):
        with self._cache_lock:
            data = self._last_pose
        if data is None:
            return
        try:
            msg = PoseStateMsg()
            # header
            msg.header.stamp = self.get_clock().now().to_msg()

            # 经度/纬度: PoseState 使用 int32，存储为度 * 1e7
            lon_deg = float(data.get_longitude_degrees() or 0.0)
            lat_deg = float(data.get_latitude_degrees() or 0.0)
            msg.longitude = int(round(lon_deg * 1e7))
            msg.latitude = int(round(lat_deg * 1e7))

            # 高度: 单位 m -> 存为 int16，值 = m * 10
            msg.altitude = int(round(float(data.get_altitude_meters() or 0.0) * 10))

            # 姿态角: rad -> 存为 int16，值 = rad * 1000
            msg.roll = int(round(float(data.get_roll_rad() or 0.0) * 1000))
            msg.pitch = int(round(float(data.get_pitch_rad() or 0.0) * 1000))
            # yaw: Revo CW → 取反偏移后归一化，车头朝真北时 yaw=0
            raw_yaw_rad = float(data.get_yaw_rad() or 0.0)
            corrected_yaw_rad = raw_yaw_rad - self._yaw_offset_rad
            # 归一化到 (-π, π]，确保跳变始终在 ±π 边界
            corrected_yaw_rad = math.atan2(math.sin(corrected_yaw_rad),
                                           math.cos(corrected_yaw_rad))
            msg.yaw = int(round(corrected_yaw_rad * 1000))

            # 融合速度: 线速度 m/s -> int16，值 = m/s * 100
            msg.fused_linear_velocity = int(round(float(data.get_fused_linear_velocity_ms() or 0.0) * 100))
            # 融合角速度: rad/s -> int16，值 = rad/s * 1000
            msg.fused_angular_velocity = int(round(float(data.get_fused_angular_velocity_rads() or 0.0) * 1000))

            # 轮速
            msg.wheel_linear_velocity = int(round(float(data.get_wheel_linear_velocity_ms() or 0.0) * 100))
            msg.wheel_angular_velocity = int(round(float(data.get_wheel_angular_velocity_rads() or 0.0) * 1000))

            self.pose_pub.publish(msg)

            # --- 同时发布标准 sensor_msgs/Imu ---
            imu_msg = Imu()
            imu_msg.header.stamp = msg.header.stamp
            imu_msg.header.frame_id = self.imu_frame_id

            # 姿态角: Revo yaw CW positive → ROS CCW positive，取反 + 偏移修正
            roll_rad = float(data.get_roll_rad() or 0.0)
            pitch_rad = float(data.get_pitch_rad() or 0.0)
            yaw_rad = -raw_yaw_rad + self._yaw_offset_rad  # 取反 + 加偏移(逆时针为正)

            # 欧拉角转四元数
            cy = math.cos(yaw_rad * 0.5)
            sy = math.sin(yaw_rad * 0.5)
            cp = math.cos(pitch_rad * 0.5)
            sp = math.sin(pitch_rad * 0.5)
            cr = math.cos(roll_rad * 0.5)
            sr = math.sin(roll_rad * 0.5)
            imu_msg.orientation.w = cr * cp * cy + sr * sp * sy
            imu_msg.orientation.x = sr * cp * cy - cr * sp * sy
            imu_msg.orientation.y = cr * sp * cy + sr * cp * sy
            imu_msg.orientation.z = cr * cp * sy - sr * sp * cy

            # 角速度: 同样取反 angular.z 以符合 ROS CCW positive
            fused_ang_vel = float(data.get_fused_angular_velocity_rads() or 0.0)
            imu_msg.angular_velocity.x = 0.0
            imu_msg.angular_velocity.y = 0.0
            imu_msg.angular_velocity.z = -fused_ang_vel  # 坐标系转换

            # 无加速度计数据: 线加速度设为 0，协方差设为 -1 表示未知 (REP-145)
            imu_msg.linear_acceleration.x = 0.0
            imu_msg.linear_acceleration.y = 0.0
            imu_msg.linear_acceleration.z = 0.0
            imu_msg.linear_acceleration_covariance[0] = -1.0

            # 协方差矩阵 (3x3 行优先, 9元素)
            # 姿态协方差: yaw 方向较准确 (0.01), roll/pitch 未知 (设较大值)
            imu_msg.orientation_covariance = [
                1e6, 0.0, 0.0,   # roll
                0.0, 1e6, 0.0,   # pitch
                0.0, 0.0, 0.01   # yaw (来自IMU，较准确)
            ]
            # 角速度协方差
            imu_msg.angular_velocity_covariance = [
                1e6, 0.0, 0.0,   # vroll: 无数据，设大值
                0.0, 1e6, 0.0,   # vpitch: 无数据
                0.0, 0.0, 0.05   # vyaw: 来自融合角速度
            ]

            self.imu_pub.publish(imu_msg)
        except Exception as e:
             self.get_logger().error(f'发布位姿数据失败: {e}')

    def _publish_system_timer(self):
        with self._cache_lock:
            data = self._last_system
        if data is None:
            return
        try:
            msg = SystemStatusMsg()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.control_mode = int(getattr(data, 'control_mode', 0))
            # reserved 三字节默认 0
            msg.reserved = [0, 0, 0]
            msg.positioning_status = int(getattr(data, 'positioning_status', 0))
            msg.battery_status = int(getattr(data, 'battery_status', 0))
            msg.chassis_status = int(getattr(data, 'chassis_status', 0))
            # motor_status: 保证为长度 8 的 uint32 列表
            motors = []
            try:
                motors = list(getattr(data, 'motor_status', []))
            except Exception:
                motors = []
            motors = [int(x) for x in (motors + [0]*8)[:8]]
            msg.motor_status = motors
            self.system_pub.publish(msg)
        except Exception as e:
             self.get_logger().error(f'发布系统状态失败: {e}')

    def _publish_battery_timer(self):
        with self._cache_lock:
            data = self._last_battery
        if data is None:
            return
        try:
            msg = BatteryStatusMsg()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.battery_count = int(getattr(data, 'battery_count', 0))
            msg.remaining_capacity = int(getattr(data, 'remaining_capacity', 0))
            msg.power = int(getattr(data, 'power', 0))
            self.battery_pub.publish(msg)
        except Exception as e:
             self.get_logger().error(f'发布电池数据失败: {e}')

    def on_control_cmd(self, msg: Twist):
        # 将 Twist 转换为 SDK 期望的尺度并发送
        try:
            # If incoming Twist is in physical units (m/s, rad/s),
            # treat linear_scale/angular_scale as maximum limits and clamp.
            if self.cmd_vel_in_physical:
                lin = float(msg.linear.x)
                ang = -float(msg.angular.z)  # 取反以符合ROS REP-103: angular.z>0左转
                # clamp to [-max, max]
                if lin > self.linear_scale:
                    lin = self.linear_scale
                if lin < -self.linear_scale:
                    lin = -self.linear_scale
                if ang > self.angular_scale:
                    ang = self.angular_scale
                if ang < -self.angular_scale:
                    ang = -self.angular_scale

                # reduce precision: linear to cm, angular to 1e-3 rad
                lin = round(lin, 2)
                ang = round(ang, 3)
                # convert to SDK units using configured multipliers
                sdk_linear = int(lin * self.sdk_linear_multiplier)
                sdk_angular = int(ang * self.sdk_angular_multiplier)
                self.sdk.send_control_command(sdk_linear, sdk_angular)
            else:
                # If incoming Twist is already in SDK units, treat linear_scale/angular_scale
                # as max SDK values and clamp accordingly.
                lin = float(msg.linear.x)
                ang = -float(msg.angular.z)  # 取反以符合ROS REP-103: angular.z>0左转
                if lin > self.linear_scale:
                    lin = self.linear_scale
                if lin < -self.linear_scale:
                    lin = -self.linear_scale
                if ang > self.angular_scale:
                    ang = self.angular_scale
                if ang < -self.angular_scale:
                    ang = -self.angular_scale
                lin = round(lin, 2)
                ang = round(ang, 3)
                sdk_linear = int(lin)
                sdk_angular = int(ang)
                self.sdk.send_control_command(sdk_linear, sdk_angular)
        except Exception as e:
            self.get_logger().error(f'发送控制命令失败: {e}')

    def destroy_node(self):
        # 清理 SDK
        with self._state_lock:
            self._running = False
        try:
            self.sdk.send_control_command(0, 0)
        except Exception:
            pass
        try:
            self.sdk.unlock(False)
        except Exception:
            pass
        try:
            self.sdk.release_control()
        except Exception:
            pass
        try:
            self.sdk.subscribe_pose(False)
            self.sdk.subscribe_battery(False)
            self.sdk.subscribe_system_status(False)
        except Exception:
            pass
        try:
            self.sdk.unregister()
            self.sdk.disconnect()
        except Exception:
            pass
        super().destroy_node()

    # GNSS/odom helpers moved to revo_odom_node.py
    pass


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = RevoBridgeNode()
    except Exception as e:
        print(f'节点初始化失败: {e}')
        rclpy.shutdown()
        return

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
