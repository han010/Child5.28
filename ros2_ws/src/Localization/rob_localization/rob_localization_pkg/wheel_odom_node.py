#!/usr/bin/env python3
"""
SDK 融合里程计发布节点

订阅 /revo/pose (PoseState)，提取 SDK 融合数据：
  - fused_linear_velocity (轮速+IMU融合)
  - fused_angular_velocity (IMU融合)
  - yaw (IMU+RTK 融合，高精度航向)

发布完整 nav_msgs/Odometry 到 /wheel_odom：
  - pose: 通过速度积分的 x, y + SDK 的 yaw
  - twist: SDK 的 fused vx, vyaw

EKF1 只需融合 /wheel_odom 即可得到平滑里程计，不再需要单独的 IMU 输入。
"""

import math
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Quaternion
from revo_msgs.msg import PoseState
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped

# 协方差常量
_COV_MEASURED = 1e-3
_COV_UNMEASURED = 1e6


def _yaw_to_quaternion(yaw: float) -> Quaternion:
    q = Quaternion()
    q.w = math.cos(yaw * 0.5)
    q.x = 0.0
    q.y = 0.0
    q.z = math.sin(yaw * 0.5)
    return q


class WheelOdomNode(Node):
    def __init__(self):
        super().__init__('wheel_odom_node')

        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('pose_topic', '/revo/pose')
        self.declare_parameter('wheel_odom_topic', '/wheel_odom')
        self.declare_parameter('use_fused_data', True)  # True=融合数据, False=原始轮速
        self.declare_parameter('publish_tf', True)

        odom_frame = self.get_parameter('odom_frame').value
        self._base_frame = self.get_parameter('base_frame').value
        pose_topic = self.get_parameter('pose_topic').value
        wheel_odom_topic = self.get_parameter('wheel_odom_topic').value
        self._use_fused = self.get_parameter('use_fused_data').value
        self._publish_tf = self.get_parameter('publish_tf').value

        self._odom_pub = self.create_publisher(Odometry, wheel_odom_topic, 10)
        if self._publish_tf:
            self._tf_broadcaster = TransformBroadcaster(self)

        # 位置积分状态
        self._x = 0.0
        self._y = 0.0
        self._yaw = 0.0        # ROS 坐标系 (CCW positive)
        self._last_stamp = None

        # 预构建协方差矩阵
        # pose: x, y 有值, yaw 有值, 其余 1e6
        self._pose_cov = [0.0] * 36
        self._pose_cov[0] = 0.01      # x
        self._pose_cov[7] = 0.01      # y
        self._pose_cov[14] = _COV_UNMEASURED   # z
        self._pose_cov[21] = _COV_UNMEASURED   # roll
        self._pose_cov[28] = _COV_UNMEASURED   # pitch
        self._pose_cov[35] = 0.01     # yaw

        # twist: vx, vyaw 有值, 其余 1e6
        self._twist_cov = [0.0] * 36
        self._twist_cov[0] = _COV_MEASURED      # vx
        self._twist_cov[7] = _COV_UNMEASURED     # vy
        self._twist_cov[14] = _COV_UNMEASURED    # vz
        self._twist_cov[21] = _COV_UNMEASURED    # vroll
        self._twist_cov[28] = _COV_UNMEASURED    # vpitch
        self._twist_cov[35] = _COV_MEASURED      # vyaw

        self.create_subscription(PoseState, pose_topic, self._on_pose, 10)

        data_source = "SDK融合" if self._use_fused else "原始轮速"
        self.get_logger().info(
            f'里程计节点已启动 ({data_source}): {pose_topic} -> {wheel_odom_topic}'
        )

    def _on_pose(self, msg: PoseState):
        # ========== 1. 提取速度 ==========
        if self._use_fused:
            vx = float(msg.fused_linear_velocity) / 100.0
            vyaw_raw = float(msg.fused_angular_velocity) / 1000.0
        else:
            vx = float(msg.wheel_linear_velocity) / 100.0
            vyaw_raw = float(msg.wheel_angular_velocity) / 1000.0

        # Revo CW positive → ROS CCW positive
        vyaw = -vyaw_raw

        # ========== 2. 提取 yaw (SDK RTK 融合) ==========
        yaw_raw = float(msg.yaw) / 1000.0   # Revo: CW positive
        yaw_ros = -yaw_raw                   # ROS: CCW positive

        # ========== 3. 位置积分 ==========
        stamp = msg.header.stamp
        if self._last_stamp is not None:
            dt = (stamp.sec + stamp.nanosec * 1e-9) - \
                 (self._last_stamp.sec + self._last_stamp.nanosec * 1e-9)
            if dt > 0.0 and dt < 1.0:   # 合理时间差 (< 1s)
                # 用 SDK 的 yaw 积分位置
                self._x += vx * math.cos(yaw_ros) * dt
                self._y += vx * math.sin(yaw_ros) * dt
        self._last_stamp = stamp
        self._yaw = yaw_ros

        # ========== 4. 发布 Odometry ==========
        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'

        # pose: 积分位置 + SDK yaw
        odom.pose.pose.position.x = self._x
        odom.pose.pose.position.y = self._y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation = _yaw_to_quaternion(yaw_ros)
        odom.pose.covariance = list(self._pose_cov)

        # twist: SDK 融合速度
        odom.twist.twist.linear.x = vx
        odom.twist.twist.angular.z = vyaw
        odom.twist.covariance = list(self._twist_cov)

        self._odom_pub.publish(odom)

        # ========== 5. 发布 TF ==========
        if self._publish_tf:
            tf = TransformStamped()
            tf.header.stamp = stamp
            tf.header.frame_id = 'odom'
            tf.child_frame_id = self._base_frame
            tf.transform.translation.x = self._x
            tf.transform.translation.y = self._y
            tf.transform.translation.z = 0.0
            tf.transform.rotation = odom.pose.pose.orientation
            self._tf_broadcaster.sendTransform(tf)


def main(args=None):
    rclpy.init(args=args)
    node = WheelOdomNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
