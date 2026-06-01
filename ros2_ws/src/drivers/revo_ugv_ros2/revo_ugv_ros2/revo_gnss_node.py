#!/usr/bin/env python3
"""
GNSS 状态发布节点

功能：
- 将底盘的 GNSS 数据转换为 ROS GPS 消息
- 发布定位状态的详细信息
- 发布定位质量指标
"""

import rclpy
from rclpy.node import Node
from revo_msgs.msg import PoseState as PoseStateMsg, SystemStatus as SystemStatusMsg
from sensor_msgs.msg import NavSatFix, NavSatStatus
from std_msgs.msg import String
import math


class RevoGNSSNode(Node):
    """Revo 底盘 GNSS 数据转换节点"""

    # 定位状态位定义
    STATUS_BITS = {
        0: ("设备离线", "在线正常", "设备离线"),
        1: ("RTK定位精度", "精度正常", "RTK定位精度低"),
        2: ("航向精度", "航向精度正常", "航向精度低"),
        3: ("板卡状态", "板卡正常", "板卡复位异常"),
        4: ("RTK模式状态", "RTK模式正常", "非RTK模式"),
        5: ("卫星数量", "卫星数充足", "卫星数过低"),
        6: ("角度融合", "角度融合正常", "角度融合出错"),
        7: ("垂直融合", "垂直融合正常", "垂直融合出错"),
        8: ("水平融合", "水平融合正常", "水平融合出错"),
        9: ("定位可用性", "有可用定位", "无定位"),
        10: ("位置准确性", "位置准确", "位置错误"),
        11: ("位置稳定性", "位置稳定", "位置跳变"),
        12: ("水平速度", "水平速度正常", "GPS水平速度异常"),
        13: ("航向数据", "航向数据正常", "GPS航向错误"),
    }

    def __init__(self):
        super().__init__('revo_gnss_node')

        # 订阅底盘数据
        self.create_subscription(PoseStateMsg, 'revo/pose', self._on_pose, 10)
        self.create_subscription(SystemStatusMsg, 'revo/system_status', self._on_system, 10)

        # 发布 GPS 数据
        self.gps_pub = self.create_publisher(NavSatFix, 'gps/fix', 10)
        self.gps_status_pub = self.create_publisher(String, 'gps/status', 10)
        self.gps_quality_pub = self.create_publisher(String, 'gps/quality', 10)

        # 缓存数据
        self._pose = None
        self._system = None
        self._earth_radius = 6378137.0

        self.get_logger().info('Revo GNSS 节点已启动')

    def _on_pose(self, msg: PoseStateMsg):
        """处理位姿数据，提取 GNSS 信息"""
        self._pose = msg
        self._publish_gps_data()

    def _on_system(self, msg: SystemStatusMsg):
        """处理系统状态数据，提取定位状态"""
        self._system = msg
        self._publish_gps_status()

    def _bit(self, status: int, n: int) -> bool:
        """检查状态位的值"""
        return bool(status & (1 << n))

    def _is_gnss_sample_good(self, status: int) -> bool:
        """判断 GNSS 样本是否有效（参考 odom_node 逻辑）"""
        if self._bit(status, 0):
            return False
        if self._bit(status, 9):
            return False
        if not self._bit(status, 4):
            if self._bit(status, 3) or self._bit(status, 6) or self._bit(status, 8):
                return False
            return True
        if self._bit(status, 5):
            return False
        if self._bit(status, 10):
            return False
        if self._bit(status, 11):
            return False
        if self._bit(status, 13) or self._bit(status, 2):
            return False
        return True

    def _publish_gps_data(self):
        """发布 GPS Fix 数据"""
        if self._pose is None:
            return

        pose = self._pose

        # 提取经纬度（单位：1/10000000度 -> 度）
        longitude = float(pose.longitude) / 1e7 if pose.longitude else 0.0
        latitude = float(pose.latitude) / 1e7 if pose.latitude else 0.0
        altitude = float(pose.altitude) / 10.0 if pose.altitude else 0.0  # 单位：1/10米 -> 米

        # 检查是否有有效的 GNSS 数据
        system_status = int(self._system.positioning_status) if self._system is not None else 0
        has_fix = self._is_gnss_sample_good(system_status) and not (longitude == 0.0 and latitude == 0.0)

        # 创建 NavSatFix 消息
        gps_msg = NavSatFix()
        gps_msg.header.stamp = self.get_clock().now().to_msg()
        gps_msg.header.frame_id = "gps"

        gps_msg.latitude = latitude
        gps_msg.longitude = longitude
        gps_msg.altitude = altitude

        # 设置定位状态
        if has_fix:
            if self._bit(system_status, 4):  # 非RTK模式
                gps_msg.status.status = NavSatStatus.STATUS_SBAS_FIX
                gps_msg.status.service = NavSatStatus.SERVICE_GPS | NavSatStatus.SERVICE_GLONASS
            else:  # RTK模式
                gps_msg.status.status = NavSatStatus.STATUS_GBAS_FIX
                gps_msg.status.service = NavSatStatus.SERVICE_GPS | NavSatStatus.SERVICE_GLONASS
        else:
            gps_msg.status.status = NavSatStatus.STATUS_NO_FIX
            gps_msg.status.service = 0

        # 设置位置协方差（基于定位状态）
        if not has_fix:
            gps_msg.position_covariance_type = NavSatFix.COVARIANCE_TYPE_UNKNOWN
            gps_msg.position_covariance = [0.0] * 9
        elif self._bit(system_status, 1):  # RTK定位精度低
            gps_msg.position_covariance_type = NavSatFix.COVARIANCE_TYPE_APPROXIMATED
            gps_msg.position_covariance = [
                10.0, 0.0, 0.0,
                0.0, 10.0, 0.0,
                0.0, 0.0, 15.0
            ]
        else:  # RTK精度正常
            gps_msg.position_covariance_type = NavSatFix.COVARIANCE_TYPE_KNOWN
            gps_msg.position_covariance = [
                0.01, 0.0, 0.0,
                0.0, 0.01, 0.0,
                0.0, 0.0, 0.02
            ]

        self.gps_pub.publish(gps_msg)

    def _publish_gps_status(self):
        """发布 GPS 状态的详细信息"""
        if self._system is None:
            return

        status = int(self._system.positioning_status)

        # 构建状态描述字符串
        status_lines = []
        for bit, (name, normal, abnormal) in self.STATUS_BITS.items():
            if self._bit(status, bit):
                status_lines.append(f"[异常] {name}: {abnormal}")
            else:
                status_lines.append(f"[正常] {name}: {normal}")

        status_msg = String()
        status_msg.data = "\n".join(status_lines)
        self.gps_status_pub.publish(status_msg)

        # 发布质量摘要
        quality_lines = []

        # 判断整体定位质量
        if self._bit(status, 0):
            quality_lines.append("状态: 设备离线")
        elif self._bit(status, 9):
            quality_lines.append("状态: 无定位")
        elif self._bit(status, 10) or self._bit(status, 11):
            quality_lines.append("状态: 定位不稳定")
        elif self._bit(status, 1):
            quality_lines.append("状态: RTK精度低")
        elif self._bit(status, 4):
            quality_lines.append("状态: 非RTK模式")
        else:
            quality_lines.append("状态: RTK固定解")

        # 添加关键指标
        if self._bit(status, 2):
            quality_lines.append("警告: 航向精度低")
        if self._bit(status, 5):
            quality_lines.append("警告: 卫星数过低")
        if self._bit(status, 6):
            quality_lines.append("错误: 角度融合出错")
        if self._bit(status, 7):
            quality_lines.append("错误: 垂直融合出错")
        if self._bit(status, 8):
            quality_lines.append("错误: 水平融合出错")

        quality_msg = String()
        quality_msg.data = " | ".join(quality_lines)
        self.gps_quality_pub.publish(quality_msg)


def main(args=None):
    rclpy.init(args=args)
    node = RevoGNSSNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()