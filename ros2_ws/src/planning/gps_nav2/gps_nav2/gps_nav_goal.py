#!/usr/bin/env python3
"""
GPS导航目标节点 - 使用Nav2进行GPS点到点和多点导航

功能:
1. 接收GPS目标点(通过服务)
2. WGS84 → ENU 局部坐标 (与 gps_to_odom_node 一致)
3. 发送目标点给Nav2导航栈
4. 支持多点航点依次执行
5. 发布导航状态

坐标系 (与 gps_to_odom_node 一致):
- map = odom: ENU 局部坐标, X=东, Y=北
- yaw: CCW positive, 0=东
- 原点: 由 gps_to_odom_node 通过 /gps_origin 发布

依赖:
- nav2_simple_commander: Nav2控制接口
"""

import math
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import QoSProfile, DurabilityPolicy

# ROS2消息
from geometry_msgs.msg import Point
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped
from gps_nav2.msg import NavGoalStatus

# Nav2 Action
from nav2_msgs.action import NavigateToPose, FollowWaypoints

# ROS2服务
from gps_nav2.srv import GPSGoal, GPSWaypointNav, GPSNavControl

# WGS84 地球半径
_EARTH_RADIUS = 6378137.0
_DEG2RAD = math.pi / 180.0


def _gps_to_local(lat: float, lon: float, lat0: float, lon0: float):
    """WGS84 → ENU 局部坐标（与 gps_to_odom_node 完全一致）"""
    lat0_rad = lat0 * _DEG2RAD
    north = (lat - lat0) * _DEG2RAD * _EARTH_RADIUS
    east = (lon - lon0) * _DEG2RAD * _EARTH_RADIUS * math.cos(lat0_rad)
    return east, north


def _local_to_gps(x: float, y: float, lat0: float, lon0: float):
    """ENU 局部坐标 → WGS84（逆变换）"""
    lat0_rad = lat0 * _DEG2RAD
    lat = y / (_EARTH_RADIUS * _DEG2RAD) + lat0
    lon = x / (_EARTH_RADIUS * _DEG2RAD * math.cos(lat0_rad)) + lon0
    return lat, lon


class GPSNavGoalNode(Node):
    def __init__(self):
        super().__init__('gps_nav_goal_node')

        # ==================== 参数声明 ====================
        self.declare_parameter('use_nav2_waypoints', True)
        self.declare_parameter('nav2_server_timeout', 10.0)
        self.declare_parameter('gps_tolerance', 2.0)
        self.declare_parameter('publish_rate', 5.0)

        # 获取参数
        self.use_nav2_waypoints = self.get_parameter('use_nav2_waypoints').value
        self.nav2_timeout = self.get_parameter('nav2_server_timeout').value
        self.gps_tolerance = self.get_parameter('gps_tolerance').value
        self.publish_rate = self.get_parameter('publish_rate').value

        # ==================== 状态变量 ====================
        # GPS原点 (从 gps_to_odom_node 获取)
        self.origin_lat = None
        self.origin_lon = None
        self.gps_initialized = False

        # 当前机器人位姿 (map坐标系)
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_yaw = 0.0

        # 航点管理
        self.waypoints_gps = []
        self.current_waypoint_index = 0
        self.is_looping = False
        self.wait_at_waypoint = 0.0
        self.nav_active = False
        self.nav_paused = False
        self.current_goal_handle = None

        # 导航状态
        self.nav_status = "idle"
        self.status_message = "Waiting for GPS origin..."

        # ==================== 回调组 ====================
        self.service_callback_group = MutuallyExclusiveCallbackGroup()
        self.sub_callback_group = MutuallyExclusiveCallbackGroup()

        # ==================== 发布器 ====================
        self.status_pub = self.create_publisher(
            NavGoalStatus, '/nav_goal_status', 10
        )

        # ==================== 订阅器 ====================
        # GPS原点 (从 gps_to_odom_node 发布, TRANSIENT_LOCAL QoS)
        self.origin_sub = self.create_subscription(
            Point,
            '/gps_origin',
            self.origin_callback,
            QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL),
            callback_group=self.sub_callback_group
        )

        # 里程计 (gps_to_odom_node 输出)
        self.odom_sub = self.create_subscription(
            Odometry,
            '/gps_odom',
            self.odom_callback,
            10,
            callback_group=self.sub_callback_group
        )

        # ==================== 服务 ====================
        self.create_service(
            GPSGoal,
            '/set_gps_goal',
            self.set_gps_goal_callback,
            callback_group=self.service_callback_group
        )

        self.create_service(
            GPSWaypointNav,
            '/set_gps_waypoints',
            self.set_gps_waypoints_callback,
            callback_group=self.service_callback_group
        )

        self.create_service(
            GPSNavControl,
            '/gps_nav_control',
            self.gps_nav_control_callback,
            callback_group=self.service_callback_group
        )

        # ==================== Nav2 Action Client ====================
        if self.use_nav2_waypoints:
            self.waypoint_follower_client = ActionClient(
                self, FollowWaypoints, '/follow_waypoints'
            )
        else:
            self.navigate_client = ActionClient(
                self, NavigateToPose, '/navigate_to_pose'
            )

        # ==================== 定时器 ====================
        self.status_timer = self.create_timer(
            1.0 / self.publish_rate,
            self.publish_status
        )

        self.get_logger().info(
            'GPS Nav Goal Node started!\n'
            f'  Nav2 Waypoints: {"Enabled" if self.use_nav2_waypoints else "Disabled"}\n'
            '  Waiting for GPS origin from /gps_origin ...'
        )

    # ==================== 回调函数 ====================

    def origin_callback(self, msg: Point):
        """GPS原点回调 - 从 gps_to_odom_node 获取原点"""
        if self.gps_initialized:
            return

        self.origin_lat = msg.x
        self.origin_lon = msg.y
        self.gps_initialized = True
        self.nav_status = "idle"
        self.status_message = "GPS initialized, ready for navigation"

        self.get_logger().info(
            f'GPS origin received from gps_to_odom_node:\n'
            f'  Lat: {self.origin_lat:.7f}, Lon: {self.origin_lon:.7f}'
        )

    def odom_callback(self, msg: Odometry):
        """里程计回调 - 更新机器人位姿"""
        self.robot_x = msg.pose.pose.position.x
        self.robot_y = msg.pose.pose.position.y

        q = msg.pose.pose.orientation
        self.robot_yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        )

    def publish_status(self):
        """发布导航状态"""
        msg = NavGoalStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "map"

        msg.status = self.nav_status
        msg.message = self.status_message

        msg.current_waypoint = self.current_waypoint_index + 1
        msg.total_waypoints = len(self.waypoints_gps) if self.waypoints_gps else 0
        msg.is_looping = self.is_looping

        if self.gps_initialized:
            lat, lon = _local_to_gps(
                self.robot_x, self.robot_y,
                self.origin_lat, self.origin_lon
            )
            msg.current_latitude = lat
            msg.current_longitude = lon
        else:
            msg.current_latitude = 0.0
            msg.current_longitude = 0.0

        if self.waypoints_gps and self.current_waypoint_index < len(self.waypoints_gps):
            target = self.waypoints_gps[self.current_waypoint_index]
            msg.target_latitude = target['latitude']
            msg.target_longitude = target['longitude']

            target_x, target_y = _gps_to_local(
                target['latitude'], target['longitude'],
                self.origin_lat, self.origin_lon
            )
            msg.distance_to_goal = math.sqrt(
                (target_x - self.robot_x)**2 + (target_y - self.robot_y)**2
            )
        else:
            msg.target_latitude = 0.0
            msg.target_longitude = 0.0
            msg.distance_to_goal = 0.0

        if msg.total_waypoints > 0:
            msg.progress_percent = (msg.current_waypoint / msg.total_waypoints) * 100.0
        else:
            msg.progress_percent = 0.0

        self.status_pub.publish(msg)

    # ==================== GPS坐标转换 ====================

    def _gps_to_map(self, lat: float, lon: float):
        """GPS → map坐标（与 gps_to_odom_node 相同公式）"""
        if not self.gps_initialized:
            raise RuntimeError("GPS not initialized yet")
        return _gps_to_local(lat, lon, self.origin_lat, self.origin_lon)

    def _map_to_gps(self, x: float, y: float):
        """map坐标 → GPS"""
        if not self.gps_initialized:
            raise RuntimeError("GPS not initialized yet")
        return _local_to_gps(x, y, self.origin_lat, self.origin_lon)

    # ==================== 服务回调 ====================

    def set_gps_goal_callback(self, request, response):
        """单点GPS导航服务"""
        if not self.gps_initialized:
            response.success = False
            response.message = "GPS not initialized yet"
            return response

        self.get_logger().info(
            f'Received GPS goal: lat={request.latitude:.8f}, lon={request.longitude:.8f}'
        )

        waypoint = {
            'latitude': request.latitude,
            'longitude': request.longitude,
            'heading': request.heading if not math.isnan(request.heading) else None
        }

        self.waypoints_gps = [waypoint]
        self.current_waypoint_index = 0
        self.is_looping = False
        self.wait_at_waypoint = 0.0

        self._start_navigation()

        response.success = True
        response.message = "GPS goal received, starting navigation"
        return response

    def set_gps_waypoints_callback(self, request, response):
        """多点GPS航点导航服务"""
        if not self.gps_initialized:
            response.success = False
            response.message = "GPS not initialized yet"
            return response

        self.waypoints_gps = []
        for wp in request.waypoints:
            self.waypoints_gps.append({
                'latitude': wp.latitude,
                'longitude': wp.longitude,
                'heading': wp.heading if not math.isnan(wp.heading) else None
            })

        self.current_waypoint_index = 0
        self.is_looping = request.loop
        self.wait_at_waypoint = request.wait_at_waypoint

        self.get_logger().info(
            f'Received {len(self.waypoints_gps)} GPS waypoints\n'
            f'  Loop: {self.is_looping}, Wait: {self.wait_at_waypoint}s'
        )

        self._start_navigation()

        response.success = True
        response.message = f"{len(self.waypoints_gps)} waypoints received"
        response.total_waypoints = len(self.waypoints_gps)
        return response

    def gps_nav_control_callback(self, request, response):
        """导航控制服务"""
        command = request.command.lower()

        if command == "pause":
            self.nav_paused = True
            self.nav_status = "paused"
            self.status_message = "Navigation paused"
            response.success = True
            response.message = "Navigation paused"

        elif command == "resume":
            if self.nav_paused:
                self.nav_paused = False
                self.nav_status = "navigating"
                self.status_message = "Navigation resumed"
                response.success = True
                response.message = "Navigation resumed"
            else:
                response.success = False
                response.message = "Navigation not paused"

        elif command == "reset":
            self.waypoints_gps = []
            self.current_waypoint_index = 0
            self.nav_active = False
            self.nav_paused = False
            self.nav_status = "idle"
            self.status_message = "Navigation reset"
            response.success = True
            response.message = "Navigation reset"

        elif command == "stop":
            self.nav_active = False
            self.nav_paused = False
            self.nav_status = "idle"
            self.status_message = "Navigation stopped"
            response.success = True
            response.message = "Navigation stopped"

        else:
            response.success = False
            response.message = f"Unknown command: {command}"

        response.current_status = self.nav_status
        return response

    # ==================== 导航控制 ====================

    def _start_navigation(self):
        """开始导航"""
        if not self.waypoints_gps:
            self.get_logger().warn("No waypoints to navigate")
            return

        if not self._wait_nav2_server():
            return

        self.nav_active = True
        self.nav_paused = False
        self.nav_status = "navigating"
        self.status_message = "Navigation started"

        waypoint_poses = []
        for wp in self.waypoints_gps:
            x, y = self._gps_to_map(wp['latitude'], wp['longitude'])
            pose = PoseStamped()
            pose.header.frame_id = "map"
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x = x
            pose.pose.position.y = y
            pose.pose.position.z = 0.0

            if wp['heading'] is not None:
                pose.pose.orientation.z = math.sin(wp['heading'] / 2.0)
                pose.pose.orientation.w = math.cos(wp['heading'] / 2.0)
            else:
                pose.pose.orientation.w = 1.0

            waypoint_poses.append(pose)

        if self.use_nav2_waypoints:
            self._send_to_waypoint_follower(waypoint_poses)
        else:
            self._send_single_goal(waypoint_poses[0])

    def _wait_nav2_server(self):
        """等待 Nav2 action server 就绪"""
        if self.use_nav2_waypoints:
            ready = self.waypoint_follower_client.wait_for_server(
                timeout_sec=self.nav2_timeout
            )
            server_name = '/follow_waypoints'
        else:
            ready = self.navigate_client.wait_for_server(
                timeout_sec=self.nav2_timeout
            )
            server_name = '/navigate_to_pose'

        if not ready:
            self.nav_status = "error"
            self.status_message = f"Nav2 server not ready: {server_name}"
            self.get_logger().error(self.status_message)
            return False

        return True

    def _send_to_waypoint_follower(self, waypoint_poses):
        """发送航点给Nav2 Waypoint Follower"""
        self.get_logger().info(
            f'Sending {len(waypoint_poses)} waypoints to Nav2'
        )
        self.waypoint_follower_client.send_goal(
            FollowWaypoints.Goal(poses=waypoint_poses)
        )

    def _send_single_goal(self, goal_pose):
        """发送单个目标给Nav2"""
        self.get_logger().info(
            f'Sending goal: x={goal_pose.pose.position.x:.2f}, '
            f'y={goal_pose.pose.position.y:.2f}'
        )
        self.navigate_client.send_goal(
            NavigateToPose.Goal(pose=goal_pose)
        )


def main(args=None):
    rclpy.init(args=args)

    node = GPSNavGoalNode()

    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
