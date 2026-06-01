#!/usr/bin/env python3
"""
Relay /scan to /scan_be with best_effort QoS for slam_toolbox compatibility.
Upstream rplidar_ros publishes RELIABLE; slam_toolbox defaults to BEST_EFFORT,
causing drops. This node republishes with best_effort.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from sensor_msgs.msg import LaserScan


class ScanRelay(Node):
    def __init__(self):
        super().__init__("scan_relay_qos")
        depth = 10
        sub_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=depth,
        )
        pub_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=depth,
        )
        self.pub = self.create_publisher(LaserScan, "/scan_be", pub_qos)
        self.sub = self.create_subscription(LaserScan, "/scan", self.cb, sub_qos)
        self.get_logger().info("Relaying /scan -> /scan_be with BEST_EFFORT QoS")

    def cb(self, msg: LaserScan):
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = ScanRelay()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
