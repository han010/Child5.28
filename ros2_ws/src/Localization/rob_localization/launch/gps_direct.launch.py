#!/usr/bin/env python3
"""
室外 GPS 直接定位启动文件

架构（简化版）:
  gps_to_odom_node: /revo/pose → /gps_odom + TF(odom_gps→base_link)

直接使用厂家 RTK+IMU 融合的经纬度和航向，转换为 ENU 局部坐标。
不需要 navsat_transform_node 和 EKF2。

使用方法:
    # 前置: revo_bridge 必须运行（提供 /revo/pose）
    ros2 launch rob_localization gps_direct.launch.py
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_path = get_package_share_directory('rob_localization')

    pose_source_arg = DeclareLaunchArgument(
        'pose_source',
        default_value='/revo/pose',
        description='位姿数据源 (PoseState)'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='使用仿真时间'
    )
    sim_time = LaunchConfiguration('use_sim_time')

    # gps_to_odom_node: 经纬度+yaw → ENU 里程计
    gps_to_odom_node = Node(
        package='rob_localization',
        executable='gps_to_odom',
        name='gps_to_odom_node',
        output='screen',
        parameters=[{
            'odom_frame': 'odom_gps',
            'base_frame': 'base_link',
            'pose_topic': LaunchConfiguration('pose_source'),
            'gps_odom_topic': '/gps_odom',
            'publish_tf': True,
            'gps_cov_xy': 0.5,
            'gps_cov_yaw': 0.05,
            'use_sim_time': sim_time,
        }]
    )

    return LaunchDescription([
        pose_source_arg,
        use_sim_time_arg,
        gps_to_odom_node,
    ])
