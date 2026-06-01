#!/usr/bin/env python3
"""
GPS→里程计转换节点

直接从 /revo/pose 提取经纬度 + RTK/IMU 融合 yaw，转换为 ENU 局部坐标系里程计。
跳过 navsat_transform_node，不依赖 /gps/fix 话题。

坐标系:
    - ENU (2D): X=东, Y=北
    - 首帧 GPS 作为原点 (origin_lat, origin_lon, origin_alt)
    - Revo yaw: 1/1000 rad, CW positive, 0=北
    - ROS yaw: CCW positive, 0=东

输出:
  /gps_odom (nav_msgs/Odometry) — 北东位置 + 航向
  /gps_origin (geometry_msgs/Point) — GPS 原点经纬度 (x=lat, y=lon)
  TF: odom → base_link
"""

import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Quaternion, TransformStamped, Point
from revo_msgs.msg import PoseState
from tf2_ros import TransformBroadcaster

# WGS84 地球半径
_EARTH_RADIUS = 6378137.0
_DEG2RAD = math.pi / 180.0

_COV_GPS_XY = 0.5        # GPS 位置协方差（米²），RTK 时可改小到 0.01
_COV_GPS_YAW = 0.05      # RTK 融合航向协方差
_COV_VEL = 0.01          # 速度协方差
_COV_UNMEASURED = 1e6


def _yaw_to_quat(yaw: float) -> Quaternion:
    q = Quaternion()
    q.w = math.cos(yaw * 0.5)
    q.x = 0.0
    q.y = 0.0
    q.z = math.sin(yaw * 0.5)
    return q


def _gps_to_local(lat: float, lon: float, lat0: float, lon0: float):
    """WGS84 经纬度 → ENU 局部平面坐标（小范围近似）

    X = 东 (经度变化), Y = 北 (纬度变化)
    ROS yaw: 0°=东, CCW 为正
    """
    lat0_rad = lat0 * _DEG2RAD
    north = (lat - lat0) * _DEG2RAD * _EARTH_RADIUS
    east = (lon - lon0) * _DEG2RAD * _EARTH_RADIUS * math.cos(lat0_rad)
    return east, north


class GpsToOdomNode(Node):
    def __init__(self):
        super().__init__('gps_to_odom_node')

        # 参数
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('pose_topic', '/revo/pose')
        self.declare_parameter('gps_odom_topic', '/gps_odom')
        self.declare_parameter('publish_tf', True)
        self.declare_parameter('gps_cov_xy', _COV_GPS_XY)
        self.declare_parameter('gps_cov_yaw', _COV_GPS_YAW)
        self.declare_parameter('min_speed_for_yaw', 0.1)

        self._odom_frame = self.get_parameter('odom_frame').value
        self._base_frame = self.get_parameter('base_frame').value
        pose_topic = self.get_parameter('pose_topic').value
        gps_odom_topic = self.get_parameter('gps_odom_topic').value
        self._publish_tf = self.get_parameter('publish_tf').value

        cov_xy = self.get_parameter('gps_cov_xy').value
        cov_yaw = self.get_parameter('gps_cov_yaw').value

        # 发布器
        self._odom_pub = self.create_publisher(Odometry, gps_odom_topic, 10)
        self._origin_pub = self.create_publisher(
            Point, '/gps_origin',
            QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        )
        if self._publish_tf:
            self._tf_broadcaster = TransformBroadcaster(self)

        # GPS 原点（首帧初始化）
        self._origin_lat = None
        self._origin_lon = None
        self._origin_alt = None

        # 上一帧（速度估计）
        self._last_x = None
        self._last_y = None
        self._last_stamp = None

        # 预构建协方差
        self._pose_cov = [0.0] * 36
        self._pose_cov[0] = cov_xy       # x
        self._pose_cov[7] = cov_xy       # y
        self._pose_cov[14] = _COV_UNMEASURED
        self._pose_cov[21] = _COV_UNMEASURED
        self._pose_cov[28] = _COV_UNMEASURED
        self._pose_cov[35] = cov_yaw     # yaw

        self._twist_cov = [0.0] * 36
        self._twist_cov[0] = _COV_VEL
        self._twist_cov[7] = _COV_UNMEASURED
        self._twist_cov[14] = _COV_UNMEASURED
        self._twist_cov[21] = _COV_UNMEASURED
        self._twist_cov[28] = _COV_UNMEASURED
        self._twist_cov[35] = _COV_VEL

        # 订阅
        self.create_subscription(PoseState, pose_topic, self._on_pose, 10)

        self.get_logger().info(
            f'GPS→Odom 节点已启动: {pose_topic} -> {gps_odom_topic} '
            f'(frame: {self._odom_frame})'
        )

    def _on_pose(self, msg: PoseState):
        # ========== 1. 提取 GPS ==========
        # PoseState: longitude/latitude 为 degrees × 10^7
        lon_deg = float(msg.longitude) / 1e7
        lat_deg = float(msg.latitude) / 1e7

        # ========== 2. 首帧初始化原点 ==========
        if self._origin_lat is None:
            self._origin_lat = lat_deg
            self._origin_lon = lon_deg
            self._origin_alt = float(msg.altitude) / 10.0
            self.get_logger().info(
                f'GPS 原点已设定: lat={lat_deg:.7f}, lon={lon_deg:.7f}'
            )
            # 发布原点供其他节点同步
            origin_msg = Point()
            origin_msg.x = lat_deg
            origin_msg.y = lon_deg
            origin_msg.z = self._origin_alt
            self._origin_pub.publish(origin_msg)

        # ========== 3. GPS → ENU 局部坐标 ==========
        x, y = _gps_to_local(lat_deg, lon_deg,
                             self._origin_lat, self._origin_lon)

        # ========== 4. Yaw 处理 ==========
        # Revo: 1/1000 rad, CW positive, 0=北
        # ROS:  CCW positive, 0=东
        # 取反: CW→CCW，然后转到东为0 (加 90deg)
        yaw_revo_raw = float(msg.yaw) / 1000.0
        yaw = -yaw_revo_raw + (math.pi / 2.0)

        # 归一化到 [-π, π]
        yaw = math.atan2(math.sin(yaw), math.cos(yaw))

        # ========== 5. 速度估计（帧间差分） ==========
        stamp = msg.header.stamp
        vx = 0.0
        vyaw = 0.0

        if self._last_stamp is not None and self._last_x is not None:
            dt = (stamp.sec + stamp.nanosec * 1e-9) - \
                 (self._last_stamp.sec + self._last_stamp.nanosec * 1e-9)
            if dt > 0.0 and dt < 2.0:
                vx = (x - self._last_x) / dt
                # 也可以用 SDK 融合速度（更平滑）
                vx_sdk = float(msg.fused_linear_velocity) / 100.0
                vyaw_sdk = -float(msg.fused_angular_velocity) / 1000.0
                vx = vx_sdk   # 优先使用 SDK 融合速度
                vyaw = vyaw_sdk

        self._last_x = x
        self._last_y = y
        self._last_stamp = stamp

        # ========== 6. 发布 Odometry ==========
        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = self._odom_frame
        odom.child_frame_id = self._base_frame

        odom.pose.pose.position.x = x
        odom.pose.pose.position.y = y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation = _yaw_to_quat(yaw)
        odom.pose.covariance = list(self._pose_cov)

        odom.twist.twist.linear.x = vx
        odom.twist.twist.angular.z = vyaw
        odom.twist.covariance = list(self._twist_cov)

        self._odom_pub.publish(odom)

        # ========== 7. 发布 TF ==========
        if self._publish_tf:
            tf = TransformStamped()
            tf.header.stamp = stamp
            tf.header.frame_id = self._odom_frame
            tf.child_frame_id = self._base_frame
            tf.transform.translation.x = x
            tf.transform.translation.y = y
            tf.transform.translation.z = 0.0
            tf.transform.rotation = odom.pose.pose.orientation
            self._tf_broadcaster.sendTransform(tf)


def main(args=None):
    rclpy.init(args=args)
    node = GpsToOdomNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
