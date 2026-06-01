#!/usr/bin/env python3
"""
GPS航点导航启动文件

支持单点和多点导航模式

使用方法：
1. 单点导航：
   ros2 launch revo_ugv_ros2 gps_waypoint_nav.launch.py

2. 多点导航：
   ros2 launch revo_ugv_ros2 gps_waypoint_nav.launch.py config:=waypoint_example.yaml

3. 自定义参数：
   ros2 launch revo_ugv_ros2 gps_waypoint_nav.launch.py \
     target_latitude:=30.2551 \
     target_longitude:=120.2941
"""

import os
import json
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # 获取包路径
    pkg_revo_ugv_ros2 = get_package_share_directory('revo_ugv_ros2')

    # ==================== 声明 launch 参数 ====================

    # 目标点参数
    target_latitude_arg = DeclareLaunchArgument(
        'target_latitude',
        default_value='30.2551044',
        description='目标纬度'
    )

    target_longitude_arg = DeclareLaunchArgument(
        'target_longitude',
        default_value='120.294113',
        description='目标经度'
    )

    # 航点列表（JSON格式）
    waypoint_list_arg = DeclareLaunchArgument(
        'waypoint_list',
        default_value='[]',
        description='航点列表 (JSON格式)'
    )

    # 导航参数
    tolerance_arg = DeclareLaunchArgument(
        'tolerance',
        default_value='1.0',
        description='到达容差(米)'
    )

    linear_speed_arg = DeclareLaunchArgument(
        'linear_speed',
        default_value='0.5',
        description='前进速度 m/s'
    )

    angular_speed_arg = DeclareLaunchArgument(
        'angular_speed',
        default_value='0.3',
        description='转向速度 rad/s'
    )

    angle_tolerance_arg = DeclareLaunchArgument(
        'angle_tolerance',
        default_value='0.1',
        description='角度容差 rad'
    )

    loop_waypoints_arg = DeclareLaunchArgument(
        'loop_waypoints',
        default_value='false',
        description='是否循环执行航点'
    )

    wait_at_waypoint_arg = DeclareLaunchArgument(
        'wait_at_waypoint',
        default_value='0.0',
        description='到达航点后等待时间(秒)'
    )

    # ==================== 导航节点 ====================

    gps_nav_node = Node(
        package='revo_ugv_ros2',
        executable='gps_waypoint_nav_odom',
        name='gps_waypoint_nav_odom',
        output='screen',
        parameters=[{
            'target_latitude': LaunchConfiguration('target_latitude'),
            'target_longitude': LaunchConfiguration('target_longitude'),
            'waypoint_list': LaunchConfiguration('waypoint_list'),
            'tolerance': LaunchConfiguration('tolerance'),
            'linear_speed': LaunchConfiguration('linear_speed'),
            'angular_speed': LaunchConfiguration('angular_speed'),
            'angle_tolerance': LaunchConfiguration('angle_tolerance'),
            'loop_waypoints': LaunchConfiguration('loop_waypoints'),
            'wait_at_waypoint': LaunchConfiguration('wait_at_waypoint'),
        }]
    )

    return LaunchDescription([
        # 参数声明
        target_latitude_arg,
        target_longitude_arg,
        waypoint_list_arg,
        tolerance_arg,
        linear_speed_arg,
        angular_speed_arg,
        angle_tolerance_arg,
        loop_waypoints_arg,
        wait_at_waypoint_arg,

        # 节点
        gps_nav_node,
    ])
