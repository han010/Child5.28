#!/usr/bin/env python3
"""
静态TF发布器 - 发布 map -> odom 的变换

用于测试GPS坐标转换，不需要EKF融合时使用。
简单地将map和odom设为同一坐标系（零偏移）。
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros import StaticTransformBroadcaster


class StaticMapOdomTF(Node):
    def __init__(self):
        super().__init__('static_map_odom_tf')

        # 参数
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('odom_frame', 'odom')

        map_frame = self.get_parameter('map_frame').value
        odom_frame = self.get_parameter('odom_frame').value

        # 创建静态TF广播器
        self._broadcaster = StaticTransformBroadcaster(self)

        # 创建变换 (map -> odom，零偏移)
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = map_frame
        t.child_frame_id = odom_frame

        # 零偏移（map和odom重合）
        t.transform.translation.x = 0.0
        t.transform.translation.y = 0.0
        t.transform.translation.z = 0.0
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = 0.0
        t.transform.rotation.w = 1.0

        # 发布
        self._broadcaster.sendTransform(t)

        self.get_logger().info(
            f'静态TF已发布: {map_frame} -> {odom_frame} (零偏移)'
        )


def main(args=None):
    rclpy.init(args=args)
    node = StaticMapOdomTF()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
