#!/usr/bin/env python3
"""
EKF 室内定位 Launch 文件

功能：启动轮速里程计节点 + 扩展卡尔曼滤波器，融合轮速 + IMU，实现室内精确定位。

前置要求：
    - revo_bridge_node 必须运行（提供 /revo/pose 和 /revo/imu）

使用方法：
    ros2 launch rob_localization ekf_indoor.launch.py

可选参数：
    config_file: EKF 配置文件路径（默认：ekf_indoor.yaml）
    pose_source: PoseState 话题名称（默认：/revo/pose）
    imu_source: IMU 话题名称（默认：/revo/imu）
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # 获取包路径
    pkg_robot_localization = get_package_share_directory('rob_localization')

    # ==================== 声明 launch 参数 ====================

    config_file_arg = DeclareLaunchArgument(
        'config_file',
        default_value=os.path.join(pkg_robot_localization, 'params', 'ekf_indoor.yaml'),
        description='EKF 配置文件路径'
    )

    pose_source_arg = DeclareLaunchArgument(
        'pose_source',
        default_value='/revo/pose',
        description='PoseState 话题名称'
    )

    imu_source_arg = DeclareLaunchArgument(
        'imu_source',
        default_value='/revo/imu',
        description='IMU 话题名称'
    )

    # ==================== 轮速里程计节点 ====================

    wheel_odom_node = Node(
        package='rob_localization',
        executable='wheel_odom',
        name='wheel_odom_node',
        output='screen',
        parameters=[{
            'pose_topic': LaunchConfiguration('pose_source'),
        }],
    )

    # ==================== EKF 节点 ====================

    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[LaunchConfiguration('config_file')],
        remappings=[
            ('imu/data', LaunchConfiguration('imu_source')),
        ]
    )

    # ==================== 返回 LaunchDescription ====================

    return LaunchDescription([
        # 参数声明
        config_file_arg,
        pose_source_arg,
        imu_source_arg,

        # 节点启动
        wheel_odom_node,
        ekf_node,
    ])
