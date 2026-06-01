#!/usr/bin/env python3
"""
GPS 导航一站式启动文件 (不建图, 局部避障)

架构:
  定位层 (ekf_outdoor):
    EKF1: wheel_odom + IMU → /odometry/filtered, TF: odom→base_link
    navsat: GPS → /odometry/gps
    EKF2: EKF1 + GPS → /odometry/global, TF: map→odom

  导航层 (Nav2):
    Planner: Navfn (allow_unknown=true, 无预建地图)
    Controller: DWA (局部避障, 激光雷达 costmap)
    Costmap: 无 static_layer, 仅激光雷达障碍物检测

  GPS 目标:
    接收 GPS 坐标 → WGS84→UTM→map → 发送给 Nav2

使用方法:
    # 1. 启动 revo_bringup
    ros2 launch revo_ugv_ros2 revo_bringup.launch.py

    # 2. 启动 GPS 导航
    ros2 launch rob_localization gps_nav.launch.py

    # 3. 发送 GPS 目标
    ros2 service call /set_gps_goal gps_nav2/srv/GPSGoal \
      "{latitude: 30.2551, longitude: 120.2941}"
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, IncludeLaunchDescription, TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    pkg_rob_loc = get_package_share_directory('rob_localization')
    pkg_gps_nav2 = get_package_share_directory('gps_nav2')
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')

    # ==================== 参数声明 ====================

    pose_source_arg = DeclareLaunchArgument(
        'pose_source', default_value='/revo/pose',
        description='位姿数据源话题'
    )

    nav2_params_arg = DeclareLaunchArgument(
        'nav2_params_file',
        default_value=os.path.join(pkg_gps_nav2, 'config', 'nav2', 'nav2_params_gps.yaml'),
        description='Nav2 参数文件'
    )

    utm_zone_arg = DeclareLaunchArgument(
        'utm_zone', default_value='51N',
        description='UTM 分区'
    )

    gps_tolerance_arg = DeclareLaunchArgument(
        'gps_tolerance', default_value='2.0',
        description='GPS 到达容差 (米)'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time', default_value='false',
        description='使用仿真时间'
    )

    # ==================== 1. 定位层: ekf_outdoor ====================

    ekf_outdoor = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_rob_loc, 'launch', 'ekf_outdoor.launch.py')
        ),
        launch_arguments={
            'pose_source': LaunchConfiguration('pose_source'),
        }.items()
    )

    # ==================== 2. 导航层: Nav2 ====================

    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav2_bringup, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'autostart': 'true',
            'params_file': LaunchConfiguration('nav2_params_file'),
        }.items()
    )

    # ==================== 3. GPS 目标节点 ====================

    gps_nav_goal_node = Node(
        package='gps_nav2',
        executable='gps_nav_goal.py',
        name='gps_nav_goal_node',
        output='screen',
        parameters=[{
            'utm_zone': LaunchConfiguration('utm_zone'),
            'use_nav2_waypoints': True,
            'nav2_server_timeout': 10.0,
            'gps_tolerance': LaunchConfiguration('gps_tolerance'),
            'publish_rate': 5.0,
        }]
    )

    # ==================== 延迟启动 ====================
    # 时序: EKF1(0s) → navsat(3s) → EKF2(5s) → Nav2(7s) → GPS目标(10s)
    # 关键: EKF2 必须在 Nav2 之前启动 (Nav2 需要 map→odom TF)

    # Nav2 等 EKF2 稳定后启动 (7s)
    nav2_delayed = TimerAction(period=7.0, actions=[nav2_bringup])

    # GPS 目标节点等 Nav2 就绪后启动 (10s)
    gps_goal_delayed = TimerAction(period=10.0, actions=[gps_nav_goal_node])

    # ==================== 返回 ====================

    return LaunchDescription([
        # 参数声明
        pose_source_arg,
        nav2_params_arg,
        utm_zone_arg,
        gps_tolerance_arg,
        use_sim_time_arg,

        # 定位层 (立即启动)
        ekf_outdoor,

        # 导航层 (延迟 4s)
        nav2_delayed,

        # GPS 目标 (延迟 8s)
        gps_goal_delayed,
    ])
