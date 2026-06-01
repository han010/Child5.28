#!/usr/bin/env python3
"""
cmd_vel 话题转发节点
Nav2 controller 发布到 /cmd_vel，Revo 订阅 /revo/cmd_vel，此节点做中继。
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class CmdVelRelay(Node):
    def __init__(self):
        super().__init__('cmd_vel_relay')
        self.create_subscription(Twist, '/cmd_vel', self._relay, 10)
        self._pub = self.create_publisher(Twist, '/revo/cmd_vel', 10)
        self.get_logger().info('cmd_vel relay: /cmd_vel -> /revo/cmd_vel')

    def _relay(self, msg: Twist):
        self._pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
