#!/usr/bin/env python3
"""
室内导航测试节点
使用 slam_toolbox 建图 + nav2 导航

功能：
1. 从地图上选择目标点进行导航
2. 支持多个航点依次导航
3. 提供初始位姿设置功能

依赖：
- slam_toolbox (地图)
- nav2 (导航栈)
- /revo/cmd_vel (速度控制)
- /odom (里程计)
- /scan (激光雷达)
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_simple_commander.robot_navigator import BasicNavigator
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from action_msgs.msg import GoalStatus
import math
import sys


class IndoorNavigator(Node):
    """
    室内导航控制器
    封装 nav2_simple_commander 提供简化的导航接口
    """

    def __init__(self):
        super().__init__('indoor_navigator')

        # 初始化 BasicNavigator
        self.navigator = BasicNavigator('indoor_navigator')

        # 导航状态
        self.is_navigating = False
        self.current_goal = None

        # 默认导航参数
        self.default_tolerance = 0.2  # 到达容差 (米)

        self.get_logger().info('Indoor Navigator initialized')
        self.get_logger().info('Waiting for map and navigation stack...')

    def wait_for_nav2(self):
        """等待 Nav2 导航栈准备就绪"""
        self.get_logger().info('Waiting for Nav2 to become active...')
        self.navigator.waitUntilNav2Active()
        self.get_logger().info('Nav2 is ready!')

    def set_initial_pose(self, x: float, y: float, theta: float = 0.0):
        """
        设置机器人初始位姿

        Args:
            x: x 坐标 (米)
            y: y 坐标 (米)
            theta: 朝向角度 (弧度), 默认朝向 0 (东)
        """
        initial_pose = PoseStamped()
        initial_pose.header.frame_id = 'map'
        initial_pose.header.stamp = self.navigator.get_clock().now().to_msg()

        initial_pose.pose.position.x = x
        initial_pose.pose.position.y = y
        initial_pose.pose.position.z = 0.0

        # 从朝向角度创建四元数
        initial_pose.pose.orientation.x = 0.0
        initial_pose.pose.orientation.y = 0.0
        initial_pose.pose.orientation.z = math.sin(theta / 2.0)
        initial_pose.pose.orientation.w = math.cos(theta / 2.0)

        self.navigator.setInitialPose(initial_pose)
        self.get_logger().info(
            f'Initial pose set to: x={x:.2f}, y={y:.2f}, theta={math.degrees(theta):.1f}°'
        )

    def goto_pose(self, x: float, y: float, theta: float = 0.0,
                  tolerance: float = None) -> bool:
        """
        导航到指定位姿

        Args:
            x: 目标 x 坐标 (米)
            y: 目标 y 坐标 (米)
            theta: 目标朝向角度 (弧度), 默认 0
            tolerance: 到达容差 (米), 默认使用 self.default_tolerance

        Returns:
            bool: 是否成功到达
        """
        if tolerance is None:
            tolerance = self.default_tolerance

        goal = PoseStamped()
        goal.header.frame_id = 'map'
        goal.header.stamp = self.navigator.get_clock().now().to_msg()

        goal.pose.position.x = x
        goal.pose.position.y = y
        goal.pose.position.z = 0.0

        goal.pose.orientation.x = 0.0
        goal.pose.orientation.y = 0.0
        goal.pose.orientation.z = math.sin(theta / 2.0)
        goal.pose.orientation.w = math.cos(theta / 2.0)

        self.get_logger().info(
            f'Navigating to: x={x:.2f}, y={y:.2f}, theta={math.degrees(theta):.1f}°'
        )

        self.is_navigating = True
        self.current_goal = (x, y, theta)

        # 开始导航
        self.navigator.goToPose(goal)

        # 等待结果
        while not self.isTaskComplete():
            feedback = self.navigator.getFeedback()
            if feedback:
                # 打印导航进度
                distance_remaining = math.sqrt(
                    (x - feedback.current_pose.pose.position.x) ** 2 +
                    (y - feedback.current_pose.pose.position.y) ** 2
                )
                self.get_logger().info(
                    f'Distance remaining: {distance_remaining:.2f}m',
                    throttle_duration_sec=1.0
                )

        result = self.navigator.getResult()
        self.is_navigating = False

        if result == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info('Goal reached successfully!')
            return True
        else:
            self.get_logger().warn(f'Navigation failed with status: {result}')
            return False

    def goto_waypoints(self, waypoints: list, tolerance: float = None) -> bool:
        """
        依次导航到多个航点

        Args:
            waypoints: 航点列表，每个航点为 (x, y, theta) 元组
                      theta 可选，默认为 0
            tolerance: 到达容差 (米)

        Returns:
            bool: 是否所有航点都成功到达
        """
        if tolerance is None:
            tolerance = self.default_tolerance

        self.get_logger().info(f'Starting waypoint navigation with {len(waypoints)} points')

        for i, wp in enumerate(waypoints):
            if len(wp) == 2:
                x, y = wp
                theta = 0.0
            else:
                x, y, theta = wp

            self.get_logger().info(f'Waypoint {i+1}/{len(waypoints)}')

            if not self.goto_pose(x, y, theta, tolerance):
                self.get_logger().error(f'Failed to reach waypoint {i+1}, aborting')
                return False

            # 在每个航点暂停一下
            self.get_logger().info('Waypoint reached, pausing for 1 second...')
            rclpy.spin_once(self, timeout_sec=1.0)

        self.get_logger().info('All waypoints reached successfully!')
        return True

    def isTaskComplete(self) -> bool:
        """检查当前导航任务是否完成"""
        return self.navigator.isTaskComplete()

    def cancel_navigation(self):
        """取消当前导航任务"""
        if self.is_navigating:
            self.navigator.cancelTask()
            self.get_logger().info('Navigation cancelled')
            self.is_navigating = False


def create_square_waypoints(center_x: float, center_y: float, size: float) -> list:
    """
    创建正方形航点序列（用于测试）

    Args:
        center_x: 中心 x 坐标
        center_y: 中心 y 坐标
        size: 正方形边长 (米)

    Returns:
        list: 航点列表 [(x, y, theta), ...]
    """
    half = size / 2.0
    return [
        (center_x + half, center_y + half, 0.0),        # 右上，朝东
        (center_x + half, center_y - half, -math.pi/2), # 右下，朝南
        (center_x - half, center_y - half, math.pi),    # 左下，朝西
        (center_x - half, center_y + half, math.pi/2),  # 左上，朝北
        (center_x, center_y, 0.0),                      # 回到中心
    ]


# ============================================================================
# 测试场景函数
# ============================================================================

def test_single_goal(nav: IndoorNavigator):
    """测试：单个目标点导航"""
    print("\n=== Test: Single Goal Navigation ===")

    # 示例：导航到地图上的某个点
    # 请根据实际地图调整坐标
    target_x = 2.0
    target_y = 1.0
    target_theta = 0.0  # 朝向东方

    success = nav.goto_pose(target_x, target_y, target_theta)

    if success:
        print("✓ Single goal test PASSED")
    else:
        print("✗ Single goal test FAILED")

    return success


def test_waypoints(nav: IndoorNavigator):
    """测试：多航点导航"""
    print("\n=== Test: Waypoint Navigation ===")

    # 示例：室内环境航点
    # 请根据实际地图调整坐标
    waypoints = [
        (1.0, 0.0, 0.0),      # 第一个点
        (2.0, 1.0, math.pi/2), # 第二个点，转向北
        (1.0, 2.0, math.pi),   # 第三个点，转向西
        (0.0, 1.0, -math.pi/2), # 第四个点，转向南
        (0.0, 0.0, 0.0),      # 回到起点
    ]

    success = nav.goto_waypoints(waypoints)

    if success:
        print("✓ Waypoint navigation test PASSED")
    else:
        print("✗ Waypoint navigation test FAILED")

    return success


def test_square_pattern(nav: IndoorNavigator):
    """测试：正方形模式导航"""
    print("\n=== Test: Square Pattern Navigation ===")

    # 以 (1, 1) 为中心，边长 2 米的正方形
    waypoints = create_square_waypoints(center_x=1.0, center_y=1.0, size=2.0)

    success = nav.goto_waypoints(waypoints)

    if success:
        print("✓ Square pattern test PASSED")
    else:
        print("✗ Square pattern test FAILED")

    return success


def main():
    rclpy.init()

    nav = IndoorNavigator()

    # 等待导航栈准备就绪
    nav.wait_for_nav2()

    # 设置初始位姿（根据实际地图调整！）
    # 第一次运行时需要设置，之后可以注释掉
    use_initial_pose = False  # 改为 True 来设置初始位姿

    if use_initial_pose:
        nav.set_initial_pose(x=0.0, y=0.0, theta=0.0)
        # 等待定位完成
        rclpy.spin_once(nav, timeout_sec=2.0)

    # 选择测试场景
    print("\n" + "="*50)
    print("Indoor Navigation Test")
    print("="*50)
    print("Available tests:")
    print("  1. Single goal navigation")
    print("  2. Multi-waypoint navigation")
    print("  3. Square pattern navigation")
    print("  4. Run all tests")
    print("="*50)

    # 可以直接指定要运行的测试，或者交互式选择
    test_mode = "1"  # 默认运行测试1

    # 从命令行参数读取测试模式
    if len(sys.argv) > 1:
        test_mode = sys.argv[1]

    results = {}

    try:
        if test_mode == "1":
            results['single_goal'] = test_single_goal(nav)

        elif test_mode == "2":
            results['waypoints'] = test_waypoints(nav)

        elif test_mode == "3":
            results['square'] = test_square_pattern(nav)

        elif test_mode == "4":
            results['single_goal'] = test_single_goal(nav)
            results['waypoints'] = test_waypoints(nav)
            results['square'] = test_square_pattern(nav)

        else:
            print(f"Unknown test mode: {test_mode}")
            print("Usage: python3 indoor_nav_test.py [1|2|3|4]")
            results = {}

        # 打印测试结果摘要
        print("\n" + "="*50)
        print("Test Results Summary")
        print("="*50)
        for test_name, passed in results.items():
            status = "✓ PASSED" if passed else "✗ FAILED"
            print(f"{test_name:20s}: {status}")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        nav.cancel_navigation()

    finally:
        nav.navigator.lifecycleShutdown()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
