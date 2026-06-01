#!/usr/bin/env python3
"""
GPS目标点Marker节点

功能:
1. 订阅机器人GPS (/gps/fix) 初始化本地坐标原点
2. 订阅/odom/initial_yaw_offset获取机器人启动时的真实地理朝向
3. 订阅GPS目标点 (/gps_goal_input) 进行坐标转换
4. 在rviz2中发布Marker可视化目标点
5. 发布PoseStamped目标给Nav2

坐标系说明:
- UTM: x=东向, y=北向
- ROS odom: x=前进, y=左侧, yaw=0为前进方向, 逆时针为正
- 转换时使用机器人启动时的真实地理朝向角(initial_yaw_offset)进行旋转
"""

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import NavSatFix
from geometry_msgs.msg import PoseStamped, Quaternion, Vector3
from visualization_msgs.msg import Marker
from std_msgs.msg import ColorRGBA
from nav_msgs.msg import Odometry

from gps_goal_tool.coordinate_converter import CoordinateConverter
import math


def quaternion_to_yaw(q: Quaternion) -> float:
    """从四元数提取yaw角 (绕z轴旋转)"""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class GPSGoalMarkerNode(Node):
    def __init__(self):
        super().__init__('gps_goal_marker_node')

        # 参数
        self.declare_parameter('utm_zone', '51N')
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('marker_scale', 1.0)
        self.declare_parameter('auto_send_nav2_goal', True)
        self.declare_parameter('origin_mode', 'auto')
        self.declare_parameter('origin_latitude', 0.0)
        self.declare_parameter('origin_longitude', 0.0)
        self.declare_parameter('use_manual_yaw', False)
        self.declare_parameter('manual_yaw_deg', 0.0)

        utm_zone = self.get_parameter('utm_zone').value
        self._map_frame = self.get_parameter('map_frame').value
        self._marker_scale = self.get_parameter('marker_scale').value
        self._auto_nav2 = self.get_parameter('auto_send_nav2_goal').value
        origin_mode = self.get_parameter('origin_mode').value
        use_manual_yaw = self.get_parameter('use_manual_yaw').value

        # 获取手动yaw参数
        self._manual_yaw = None
        if use_manual_yaw:
            yaw_deg = self.get_parameter('manual_yaw_deg').value
            self._manual_yaw = math.radians(yaw_deg)

        # 坐标转换器
        self._converter = CoordinateConverter(utm_zone=utm_zone)
        self.get_logger().info(f'坐标转换器已初始化, UTM zone: {utm_zone}')

        # 机器人朝向记录
        self._utm_to_robot_angle = None  # 机器人前进方向相对于正北的角度

        # 原点初始化
        if origin_mode == 'manual':
            lat = self.get_parameter('origin_latitude').value
            lon = self.get_parameter('origin_longitude').value
            if lat != 0.0 and lon != 0.0:
                self._converter.set_origin(lat, lon)
                self.get_logger().info(f'手动设置原点GPS: ({lat:.8f}, {lon:.8f})')
                if self._manual_yaw is not None:
                    self._utm_to_robot_angle = self._manual_yaw
                    self.get_logger().info(f'手动设置航向角: {math.degrees(self._manual_yaw):.1f}°')
            else:
                self.get_logger().warn('origin_mode=manual 但GPS坐标为0')

        # Marker ID计数
        self._marker_id = 0

        # 发布器
        self._marker_pub = self.create_publisher(Marker, '/gps_goal_marker', 10)
        self._goal_pub = self.create_publisher(PoseStamped, '/goal_pose', 10)

        # 订阅器
        self._odom_sub = self.create_subscription(
            Odometry, '/odom', self._on_odom, 10
        )
        self._initial_yaw_sub = self.create_subscription(
            Vector3, '/odom/initial_yaw_offset', self._on_initial_yaw, 10
        )
        self._gps_sub = self.create_subscription(
            NavSatFix, '/gps/fix', self._on_gps_fix, 10
        )
        self._goal_input_sub = self.create_subscription(
            NavSatFix, '/gps_goal_input', self._on_goal_input, 10
        )

        self.get_logger().info(
            'GPS目标点工具已启动\n'
            f'  原点模式: {origin_mode}\n'
            f'  航向角: {"手动指定" if self._manual_yaw else "从odom/initial_yaw_offset获取"}\n'
            f'  输入GPS目标点: ros2 topic pub /gps_goal_input sensor_msgs/msg/NavSatFix ...'
        )

    def _on_odom(self, msg: Odometry):
        """odom回调 - 保留用于兼容性，但不再使用odom的yaw"""
        # yaw角度现在从/odom/initial_yaw_offset获取
        pass

    def _on_initial_yaw(self, msg: Vector3):
        """接收odom启动时的初始yaw偏移量（相对于真北）"""
        # 如果手动指定了yaw，不覆盖
        if self._manual_yaw is not None:
            return

        # 如果已经记录了原点朝向，不再更新
        if self._utm_to_robot_angle is not None:
            return

        # 从odom获取真实的地理朝向角（相对于真北，ROS坐标系）
        # msg.x就是initial_yaw_offset，是机器人启动时相对于真北的角度
        # 这个角度已经是转换后的（顺时针为正→逆时针为正）
        yaw = msg.x
        self._utm_to_robot_angle = yaw
        self.get_logger().info(
            f'收到odom初始yaw偏移: {math.degrees(yaw):.1f}° '
            f'(机器人前进方向相对于正北的角度, ROS坐标系, 逆时针为正)'
        )

    def _on_gps_fix(self, msg: NavSatFix):
        """机器人GPS回调 - 初始化本地坐标原点"""
        if self._converter.initialized:
            return
        if msg.status.status < 0:
            return

        self._converter.set_origin(msg.latitude, msg.longitude)
        self.get_logger().info(
            f'GPS原点已设置!\n'
            f'  纬度: {msg.latitude:.8f}\n'
            f'  经度: {msg.longitude:.8f}'
        )

    def _on_goal_input(self, msg: NavSatFix):
        """GPS目标点回调 - 转换坐标并发布Marker"""
        self.get_logger().info(f'收到GPS目标点: ({msg.latitude:.8f}, {msg.longitude:.8f})')

        if not self._converter.initialized:
            self.get_logger().error('GPS原点尚未初始化，无法转换坐标')
            self.get_logger().info(f'请确认: /gps/fix 是否正在发布数据')
            return

        if self._utm_to_robot_angle is None:
            self.get_logger().error('机器人朝向尚未初始化，无法转换坐标')
            self.get_logger().info(f'请确认: /odom/initial_yaw_offset 是否正在发布数据')
            return

        lat, lon = msg.latitude, msg.longitude

        # GPS → UTM坐标 (x=东, y=北)
        try:
            x_utm, y_utm = self._converter.gps_to_local(lat, lon)
        except RuntimeError as e:
            self.get_logger().error(f'坐标转换失败: {e}')
            return

        # UTM坐标系转ROS机器人坐标系
        # UTM: x=东, y=北
        # ROS: x=前进, y=左, yaw逆时针为正
        #
        # 旋转矩阵推导:
        # 设机器人前进方向相对于正北的角度为θ（顺时针为正）
        # 则:
        #   x_robot = x_east * sin(θ) + y_north * cos(θ)
        #   y_robot = -x_east * cos(θ) + y_north * sin(θ)
        #
        # 但ROS的yaw是逆时针为正，所以需要取反
        # yaw_ros = -θ

        theta = -self._utm_to_robot_angle  # 转换为逆时针为正
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        x_robot = x_utm * sin_t + y_utm * cos_t
        y_robot = -x_utm * cos_t + y_utm * sin_t

        self.get_logger().info(
            f'GPS目标点: ({lat:.8f}, {lon:.8f})\n'
            f'  UTM: ({x_utm:.2f}m, {y_utm:.2f}m) [东,北]\n'
            f'  机器人: ({x_robot:.2f}m, {y_robot:.2f}m) [前,左]\n'
            f'  旋转角: {math.degrees(self._utm_to_robot_angle):.1f}°'
        )

        # 发布rviz2 Marker
        self._publish_marker(x_robot, y_robot, lat, lon)

        # 发布Nav2目标
        if self._auto_nav2:
            self._publish_nav2_goal(x_robot, y_robot)

    def _publish_marker(self, x: float, y: float, lat: float, lon: float):
        """在rviz2中发布目标点Marker"""
        marker = Marker()
        marker.header.frame_id = self._map_frame
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = 'gps_goal'
        marker.id = self._marker_id
        marker.type = Marker.ARROW
        marker.action = Marker.ADD

        marker.pose.position.x = x
        marker.pose.position.y = y
        marker.pose.position.z = 0.0
        marker.pose.orientation.w = 1.0

        s = self._marker_scale
        marker.scale.x = s * 1.0
        marker.scale.y = s * 0.2
        marker.scale.z = s * 0.2

        marker.color = ColorRGBA(r=1.0, g=0.0, b=0.0, a=1.0)
        marker.lifetime.sec = 0

        self._marker_pub.publish(marker)
        self._marker_id += 1

        # 文本标签
        text = Marker()
        text.header = marker.header
        text.ns = 'gps_goal_text'
        text.id = self._marker_id
        text.type = Marker.TEXT_VIEW_FACING
        text.action = Marker.ADD
        text.pose.position.x = x
        text.pose.position.y = y
        text.pose.position.z = s * 1.5
        text.pose.orientation.w = 1.0
        text.scale.z = s * 0.3
        text.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
        text.text = f'({lat:.6f}, {lon:.6f})\n({x:.1f}, {y:.1f})m'
        text.lifetime.sec = 0

        self._marker_pub.publish(text)
        self._marker_id += 1

    def _publish_nav2_goal(self, x: float, y: float):
        """发布Nav2导航目标"""
        goal = PoseStamped()
        goal.header.frame_id = self._map_frame
        goal.header.stamp = self.get_clock().now().to_msg()
        goal.pose.position.x = x
        goal.pose.position.y = y
        goal.pose.position.z = 0.0
        goal.pose.orientation.w = 1.0

        self._goal_pub.publish(goal)
        self.get_logger().info(f'Nav2目标已发送: ({x:.2f}, {y:.2f})')


def main(args=None):
    rclpy.init(args=args)
    node = GPSGoalMarkerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
