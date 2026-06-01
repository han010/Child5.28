#!/usr/bin/env python3
"""
简单的GPS点到点导航控制节点
使用极坐标控制策略: 先转向目标，再直线前进
"""

import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix
from revo_msgs.msg import PoseState
from geometry_msgs.msg import Twist


class GPSWaypointNavigator(Node):
    def __init__(self):
        super().__init__('gps_waypoint_nav')

        # 声明参数
        # 目标地点
        # self.declare_parameter('target_latitude', 30.2552772)
        # self.declare_parameter('target_longitude', 120.2940727)

        #开始地点
        self.declare_parameter('target_latitude', 30.2552101)
        self.declare_parameter('target_longitude', 120.2941207)
        self.declare_parameter('tolerance', 2.0)  # 到达容差(米)
        self.declare_parameter('linear_speed', 0.2)  # 前进速度 m/s
        self.declare_parameter('angular_speed', 0.2)  # 转向速度 rad/s
        self.declare_parameter('angle_tolerance', 0.1)  # 角度容差 rad (~3度)
        self.declare_parameter('adaptive_correction_kp', 0.5)  # 比例系数
        self.declare_parameter('max_correction_ratio', 0.3)  # 最大修正速度比例

        # 获取参数
        self.target_lat = self.get_parameter('target_latitude').value
        self.target_lon = self.get_parameter('target_longitude').value
        self.tolerance = self.get_parameter('tolerance').value
        self.linear_speed = self.get_parameter('linear_speed').value
        self.angular_speed = self.get_parameter('angular_speed').value
        self.angle_tolerance = self.get_parameter('angle_tolerance').value
        self.adaptive_correction_kp = self.get_parameter('adaptive_correction_kp').value
        self.max_correction_ratio = self.get_parameter('max_correction_ratio').value

        # 状态变量
        self.current_lat = None
        self.current_lon = None
        self.current_yaw = None  # 弧度
        self.gps_ready = False
        self.goal_reached = False

        # 发布器
        self.cmd_vel_pub = self.create_publisher(Twist, '/revo/cmd_vel', 10)

        # 订阅器
        self.gps_sub = self.create_subscription(
            NavSatFix,
            '/gps/fix',
            self.gps_callback,
            10
        )

        self.pose_sub = self.create_subscription(
            PoseState,
            '/revo/pose',
            self.pose_callback,
            10
        )

        # 控制定时器 (10Hz)
        self.create_timer(0.1, self.control_loop)

        self.get_logger().info(
            f'GPS Waypoint Navigator started!\n'
            f'  Target: ({self.target_lat:.8f}, {self.target_lon:.8f})\n'
            f'  Tolerance: {self.tolerance}m\n'
            f'  Speed: {self.linear_speed}m/s\n'
            f'  Waiting for GPS and pose data...'
        )

    def gps_callback(self, msg: NavSatFix):
        """GPS回调 - 更新当前位置"""
        if msg.status.status >= 0:  # 有有效定位
            self.current_lat = msg.latitude
            self.current_lon = msg.longitude

            if not self.gps_ready:
                self.gps_ready = True
                self.get_logger().info(
                    f'GPS locked! Current position: '
                    f'({self.current_lat:.8f}, {self.current_lon:.8f})'
                )

    def pose_callback(self, msg: PoseState):
        """姿态回调 - 更新当前航向角"""
        # Revo的yaw是相对于正北的绝对角度（右手系：右转为正）
        # calculate_bearing也是相对于正北的（右手系）
        # 两者在同一参考系，直接使用，不需要转换
        self.current_yaw = msg.yaw / 1000.0  # 转换为弧度

    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """
        计算从点1到点2的方位角
        返回: 弧度，范围[-pi, pi]
        """
        # 转换为弧度
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)

        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) -
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))

        bearing = math.atan2(y, x)
        return bearing

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        使用Haversine公式计算两点间距离(米)
        """
        R = 6371000  # 地球半径(米)

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = lat2_rad - lat1_rad
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat/2)**2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def normalize_angle(self, angle):
        """将角度规范化到[-pi, pi]"""
        return math.atan2(math.sin(angle), math.cos(angle))

    def control_loop(self):
        """主控制循环"""
        cmd = Twist()

        # 检查数据是否就绪
        if not self.gps_ready or self.current_yaw is None:
            return

        if self.goal_reached:
            return

        # 计算到目标的距离和方位
        distance = self.calculate_distance(
            self.current_lat, self.current_lon,
            self.target_lat, self.target_lon
        )

        # 检查是否到达
        if distance < self.tolerance:
            self.goal_reached = True
            self.get_logger().info(
                f'Goal reached! Final distance: {distance:.2f}m'
            )
            cmd.linear.x = 0.0
            cmd.angular.z = 0.0
            self.cmd_vel_pub.publish(cmd)
            return

        # 计算目标方位角
        target_bearing = self.calculate_bearing(
            self.current_lat, self.current_lon,
            self.target_lat, self.target_lon
        )

        # 计算需要的转向角度
        angle_error = self.normalize_angle(target_bearing - self.current_yaw)

        # 打印调试信息
        self.get_logger().info(
            f'Distance: {distance:.2f}m | '
            f'Yaw: {math.degrees(self.current_yaw):.1f}° | '
            f'Target Bearing: {math.degrees(target_bearing):.1f}° | '
            f'Error: {math.degrees(angle_error):.1f}°',
            throttle_duration_sec=1.0
        )

        # 极坐标控制: 先转向，再前进
        # 反转angle_error符号以适应Revo的转向约定
        angle_error = -angle_error

        if abs(angle_error) > self.angle_tolerance:
            # 纯转向阶段
            cmd.angular.z = self.angular_speed if angle_error > 0 else -self.angular_speed
            cmd.linear.x = 0.0
        else:
            # 前进阶段 - 自适应修正
            # 根据角度误差大小动态调整修正强度（P控制器）
            kp = self.adaptive_correction_kp
            max_ratio = self.max_correction_ratio

            # 计算修正速度：误差越大，修正越强
            correction = kp * self.angular_speed * (angle_error / self.angle_tolerance)

            # 限制最大修正速度
            max_correction = max_ratio * self.angular_speed
            correction = max(-max_correction, min(max_correction, correction))

            cmd.linear.x = self.linear_speed
            cmd.angular.z = correction

        self.cmd_vel_pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)

    node = GPSWaypointNavigator()

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
