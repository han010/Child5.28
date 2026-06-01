#!/usr/bin/env python3
"""
在 RViz 中显示目标坐标点的多种方法

使用方法:
1. 启动 RViz: rviz2
2. 添加 Marker 显示: Add -> Marker -> Topic: /goal_marker
3. 运行此脚本: python3 show_goal_marker.py
"""

import rclpy
from rclpy.node import Node
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point, Quaternion
import math

class GoalMarkerPublisher(Node):
    def __init__(self):
        super().__init__('goal_marker_publisher')
        self.marker_pub = self.create_publisher(Marker, '/goal_marker', 10)
        self.marker_array_pub = self.create_publisher(MarkerArray, '/goal_marker_array', 10)
        self.point_pub = self.create_publisher(Point, '/target_point', 10)

        # 定时器 - 持续发布以保持显示
        self.timer = self.create_timer(1.0, self.publish_markers)
        self.get_logger().info('目标坐标点发布节点已启动')

    def publish_markers(self):
        """发布多种类型的目标标记"""

        # ========== 方法1: 红色球体标记 ==========
        self.publish_sphere_marker()

        # ========== 方法2: 箭头标记（指向目标方向）==========
        self.publish_arrow_marker()

        # ========== 方法3: 文本标记 ==========
        self.publish_text_marker()

        # ========== 方法4: 多个点（路径点）==========
        self.publish_path_markers()

        # ========== 方法5: 简单 Point 消息（用于简单可视化）==========
        self.publish_simple_point()

    def publish_sphere_marker(self):
        """方法1: 显示一个红色球体"""
        marker = Marker()
        marker.header.frame_id = "odom"
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "goal"
        marker.id = 0
        marker.type = Marker.SPHERE
        marker.action = Marker.ADD

        # 位置
        marker.pose.position.x = 2.0
        marker.pose.position.y = 1.5
        marker.pose.position.z = 0.0

        # 方向（球体不需要，但必须设置）
        marker.pose.orientation.w = 1.0

        # 大小
        marker.scale.x = 0.3
        marker.scale.y = 0.3
        marker.scale.z = 0.3

        # 颜色 (红色)
        marker.color.r = 1.0
        marker.color.g = 0.0
        marker.color.b = 0.0
        marker.color.a = 1.0

        marker.lifetime.sec = 0  # 永久显示

        self.marker_pub.publish(marker)
        self.get_logger().info('发布球体标记: (2.0, 1.5, 0.0)')

    def publish_arrow_marker(self):
        """方法2: 显示一个箭头（指向目标方向）"""
        marker = Marker()
        marker.header.frame_id = "odom"
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "goal"
        marker.id = 1
        marker.type = Marker.ARROW
        marker.action = Marker.ADD

        # 起点
        start = Point()
        start.x = 0.0
        start.y = 0.0
        start.z = 0.0

        # 终点（目标点）
        end = Point()
        end.x = 2.0
        end.y = 1.5
        end.z = 0.0

        marker.points = [start, end]

        # 箭头粗细
        marker.scale.x = 0.1  # 轴宽度
        marker.scale.y = 0.2  # 头部宽度
        marker.scale.z = 0.3  # 头部长度

        # 颜色 (绿色)
        marker.color.r = 0.0
        marker.color.g = 1.0
        marker.color.b = 0.0
        marker.color.a = 1.0

        marker.lifetime.sec = 0

        self.marker_pub.publish(marker)
        self.get_logger().info('发布箭头标记: 从原点到(2.0, 1.5, 0.0)')

    def publish_text_marker(self):
        """方法3: 显示文本标签"""
        marker = Marker()
        marker.header.frame_id = "odom"
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = "goal"
        marker.id = 2
        marker.type = Marker.TEXT_VIEW_FACING
        marker.action = Marker.ADD

        # 位置
        marker.pose.position.x = 2.0
        marker.pose.position.y = 1.8
        marker.pose.position.z = 0.5

        marker.pose.orientation.w = 1.0

        # 文字大小
        marker.scale.z = 0.3  # 字体高度

        # 文字内容
        marker.text = "目标点"

        # 颜色 (黄色)
        marker.color.r = 1.0
        marker.color.g = 1.0
        marker.color.b = 0.0
        marker.color.a = 1.0

        marker.lifetime.sec = 0

        self.marker_pub.publish(marker)
        self.get_logger().info('发布文本标记')

    def publish_path_markers(self):
        """方法4: 显示路径点序列"""
        marker_array = MarkerArray()

        # 定义路径点
        waypoints = [
            (1.0, 0.0, 0.0),
            (1.5, 0.5, 0.0),
            (2.0, 1.5, 0.0),
            (2.5, 2.0, 0.0),
        ]

        for i, (x, y, z) in enumerate(waypoints):
            marker = Marker()
            marker.header.frame_id = "odom"
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = "path"
            marker.id = i
            marker.type = Marker.CUBE
            marker.action = Marker.ADD

            marker.pose.position.x = x
            marker.pose.position.y = y
            marker.pose.position.z = z
            marker.pose.orientation.w = 1.0

            marker.scale.x = 0.15
            marker.scale.y = 0.15
            marker.scale.z = 0.15

            # 颜色渐变（从蓝到紫）
            marker.color.r = i * 0.2
            marker.color.g = 0.0
            marker.color.b = 1.0 - i * 0.2
            marker.color.a = 0.8

            marker.lifetime.sec = 0

            marker_array.markers.append(marker)

        self.marker_array_pub.publish(marker_array)
        self.get_logger().info(f'发布路径标记: {len(waypoints)} 个点')

    def publish_simple_point(self):
        """方法5: 简单的 Point 消息"""
        point = Point()
        point.x = 2.0
        point.y = 1.5
        point.z = 0.0

        self.point_pub.publish(point)
        self.get_logger().info('发布简单点消息')


def main(args=None):
    rclpy.init(args=args)
    node = GoalMarkerPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
