#!/usr/bin/env python3
"""
GPS 直连 Nav2 户外导航启动文件

架构 (简化版, 替代 EKF1→navsat→EKF2):
  gps_to_odom_node: /revo/pose → /gps_odom + TF(odom→base_link) + /gps_origin
  静态 TF: map → odom (identity)
  Nav2: Navfn规划 + DWB控制 + 雷达避障
  gps_nav_goal: GPS目标服务

TF 树:
  map (identity) → odom → base_link

使用方法:
    # 1. 启动 revo_bringup
    ros2 launch revo_ugv_ros2 revo_bringup.launch.py

    # 2. 启动 GPS 直连导航
    ros2 launch rob_localization gps_nav_direct.launch.py

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
from launch.substitutions import LaunchConfiguration
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

    gps_tolerance_arg = DeclareLaunchArgument(
        'gps_tolerance', default_value='2.0',
        description='GPS 到达容差 (米)'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time', default_value='false',
        description='使用仿真时间'
    )
    sim_time = LaunchConfiguration('use_sim_time')

    # ==================== 1. GPS→Odom 节点 ====================

    gps_to_odom_node = Node(
        package='rob_localization',
        executable='gps_to_odom',
        name='gps_to_odom_node',
        output='screen',
        parameters=[{
            'odom_frame': 'odom',
            'base_frame': 'base_link',
            'pose_topic': LaunchConfiguration('pose_source'),
            'gps_odom_topic': '/gps_odom',
            'publish_tf': True,
            'use_sim_time': sim_time,
        }]
    )

    # ==================== 2. 静态 TF: map → odom (identity) ====================

    map_to_odom_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='map_to_odom_tf',
        arguments=['0', '0', '0', '0', '0', '0', '1', 'map', 'odom'],
        parameters=[{'use_sim_time': sim_time}]
    )

    # ==================== 3. Nav2 导航栈 ====================

    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav2_bringup, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': sim_time,
            'autostart': 'true',
            'params_file': LaunchConfiguration('nav2_params_file'),
        }.items()
    )

    # ==================== 3b. cmd_vel 转发 ====================
    # Nav2 Humble controller 硬编码发布 /cmd_vel，Revo 订阅 /revo/cmd_vel

    cmd_vel_relay = Node(
        package='rob_localization',
        executable='cmd_vel_relay',
        name='cmd_vel_relay',
        output='screen',
    )

    # ==================== 4. GPS 目标节点 ====================

    gps_nav_goal_node = Node(
        package='gps_nav2',
        executable='gps_nav_goal.py',
        name='gps_nav_goal_node',
        output='screen',
        parameters=[{
            'use_nav2_waypoints': True,
            'nav2_server_timeout': 10.0,
            'gps_tolerance': LaunchConfiguration('gps_tolerance'),
            'publish_rate': 5.0,
        }]
    )

    # ==================== 延迟启动 ====================
    # Nav2 等 gps_to_odom 稳定后 (2s)
    nav2_delayed = TimerAction(period=2.0, actions=[nav2_bringup])

    # GPS 目标等 Nav2 就绪后 (5s)
    gps_goal_delayed = TimerAction(period=5.0, actions=[gps_nav_goal_node])

    # ==================== 返回 ====================

    return LaunchDescription([
        # 参数
        pose_source_arg,
        nav2_params_arg,
        gps_tolerance_arg,
        use_sim_time_arg,

        # 立即启动: gps_to_odom + map→odom TF + cmd_vel relay
        gps_to_odom_node,
        map_to_odom_tf,
        cmd_vel_relay,

        # 延迟: Nav2 (2s) + GPS目标 (5s)
        nav2_delayed,
        gps_goal_delayed,
    ])
