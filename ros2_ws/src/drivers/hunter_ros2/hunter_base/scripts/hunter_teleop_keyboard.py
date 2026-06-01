#!/usr/bin/env python3

"""
Simple keyboard teleop for Hunter that publishes geometry_msgs/Twist.
Keys (按下即动，松开/无输入即停):
  w/s : 前进/后退
  a/d : 左转/右转
  q/z : 增加/减小速度上限
  空格/回车 : 急停
"""

import sys
import termios
import tty
from select import select
import time

import rclpy
from geometry_msgs.msg import Twist


MAX_LIN_DEFAULT = 1.0
MAX_ANG_DEFAULT = 1.0
CMD_LIN = 0.4
CMD_ANG = 0.8


class KeyboardTeleop:
    def __init__(self):
        rclpy.init()
        self.node = rclpy.create_node("hunter_teleop_keyboard")
        self.pub = self.node.create_publisher(Twist, "/cmd_vel", 10)
        self.settings = termios.tcgetattr(sys.stdin)

        self.max_lin = MAX_LIN_DEFAULT
        self.max_ang = MAX_ANG_DEFAULT
        self.target_lin = 0.0
        self.target_ang = 0.0
        self.last_key_time = time.monotonic()
        self.idle_timeout = 0.5

        self.node.get_logger().info(self._help_text())

    def _help_text(self) -> str:
        return (
            "\nKeyboard control:\n"
            "  w/s : 前进 / 后退\n"
            "  a/d : 左转 / 右转\n"
            "  q/z : 增加 / 减小速度上限\n"
            "  空格/回车 : 急停\n"
            "  松开或无输入时自动停止\n"
            "Current max => linear: %.2f m/s angular: %.2f rad/s\n"
            % (self.max_lin, self.max_ang)
        )

    def get_key(self):
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select([sys.stdin], [], [], 0.1)
        if rlist:
            key = sys.stdin.read(1)
        else:
            key = ""
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key

    def clip(self, val, limit):
        if val > limit:
            return limit
        if val < -limit:
            return -limit
        return val

    def publish_cmd(self):
        msg = Twist()
        msg.linear.x = self.clip(self.target_lin, self.max_lin)
        msg.angular.z = self.clip(self.target_ang, self.max_ang)
        self.pub.publish(msg)

    def run(self):
        try:
            while rclpy.ok():
                key = self.get_key()
                now = time.monotonic()

                if key:
                    self.last_key_time = now

                if key in ("w", "W"):
                    self.target_lin = min(self.max_lin, CMD_LIN)
                elif key in ("s", "S"):
                    self.target_lin = -min(self.max_lin, CMD_LIN)
                elif key in ("a", "A"):
                    self.target_ang = min(self.max_ang, CMD_ANG)
                elif key in ("d", "D"):
                    self.target_ang = -min(self.max_ang, CMD_ANG)
                elif key in (" ", "\r", "\n"):
                    self.target_lin = 0.0
                    self.target_ang = 0.0
                elif key in ("q", "Q"):
                    self.max_lin += 0.1
                    self.max_ang += 0.1
                    self.node.get_logger().info(
                        f"Increase limits -> lin {self.max_lin:.2f}, ang {self.max_ang:.2f}"
                    )
                elif key in ("z", "Z"):
                    self.max_lin = max(0.1, self.max_lin - 0.1)
                    self.max_ang = max(0.1, self.max_ang - 0.1)
                    self.node.get_logger().info(
                        f"Decrease limits -> lin {self.max_lin:.2f}, ang {self.max_ang:.2f}"
                    )
                elif key in ("\x03",):  # Ctrl+C
                    break

                # 超过空闲时间自动停止，避免无输入时继续运动
                if (now - self.last_key_time) > self.idle_timeout:
                    self.target_lin = 0.0
                    self.target_ang = 0.0

                self.publish_cmd()
                rclpy.spin_once(self.node, timeout_sec=0.0)
        finally:
            # send zero cmd on exit
            self.target_lin = 0.0
            self.target_ang = 0.0
            self.publish_cmd()
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
            self.node.destroy_node()
            rclpy.shutdown()


def main():
    teleop = KeyboardTeleop()
    teleop.run()


if __name__ == "__main__":
    main()
