#!/usr/bin/env python3
"""
GPS目标点工具启动文件

使用方法:
  ros2 launch gps_goal_tool gps_goal_tool.launch.py

发送GPS目标点:
  ros2 topic pub --once /gps_goal_input sensor_msgs/msg/NavSatFix \
    "{latitude: 30.2551, longitude: 120.2941, altitude: 0.0}"
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory('gps_goal_tool')

    # 参数声明
    utm_zone_arg = DeclareLaunchArgument(
        'utm_zone', default_value='51N',
        description='UTM分区 (中国东部: 51N)'
    )

    map_frame_arg = DeclareLaunchArgument(
        'map_frame', default_value='map',
        description='map坐标系名称'
    )

    auto_nav2_arg = DeclareLaunchArgument(
        'auto_send_nav2_goal', default_value='true',
        description='是否自动发送Nav2导航目标'
    )

    marker_scale_arg = DeclareLaunchArgument(
        'marker_scale', default_value='1.0',
        description='Marker可视化缩放'
    )

    origin_mode_arg = DeclareLaunchArgument(
        'origin_mode', default_value='auto',
        description='原点模式: auto(从GPS话题) 或 manual(手动指定)'
    )

    origin_lat_arg = DeclareLaunchArgument(
        'origin_latitude', default_value='0.0',
        description='手动原点纬度 (仅manual模式)'
    )

    origin_lon_arg = DeclareLaunchArgument(
        'origin_longitude', default_value='0.0',
        description='手动原点经度 (仅manual模式)'
    )

    use_manual_yaw_arg = DeclareLaunchArgument(
        'use_manual_yaw', default_value='false',
        description='是否使用手动指定航向角'
    )

    manual_yaw_arg = DeclareLaunchArgument(
        'manual_yaw_deg', default_value='0.0',
        description='手动指定航向角(度)'
    )

    publish_static_tf_arg = DeclareLaunchArgument(
        'publish_static_tf', default_value='true',
        description='是否发布静态 map->odom TF (测试用)'
    )

    # GPS目标点Marker节点
    gps_goal_marker_node = Node(
        package='gps_goal_tool',
        executable='gps_goal_marker',
        name='gps_goal_marker_node',
        output='screen',
        parameters=[{
            'utm_zone': LaunchConfiguration('utm_zone'),
            'map_frame': LaunchConfiguration('map_frame'),
            'marker_scale': LaunchConfiguration('marker_scale'),
            'auto_send_nav2_goal': LaunchConfiguration('auto_send_nav2_goal'),
            'origin_mode': LaunchConfiguration('origin_mode'),
            'origin_latitude': LaunchConfiguration('origin_latitude'),
            'origin_longitude': LaunchConfiguration('origin_longitude'),
            'use_manual_yaw': LaunchConfiguration('use_manual_yaw'),
            'manual_yaw_deg': LaunchConfiguration('manual_yaw_deg'),
        }],
    )

    # 静态 map->odom TF 发布器 (测试用)
    # 注意：如果要控制是否启动，修改此参数
    static_map_odom_tf_node = Node(
        package='gps_goal_tool',
        executable='static_map_odom_tf',
        name='static_map_odom_tf',
        output='screen',
        parameters=[{
            'map_frame': LaunchConfiguration('map_frame'),
        }],
    )

    return LaunchDescription([
        utm_zone_arg,
        map_frame_arg,
        auto_nav2_arg,
        marker_scale_arg,
        origin_mode_arg,
        origin_lat_arg,
        origin_lon_arg,
        use_manual_yaw_arg,
        manual_yaw_arg,
        publish_static_tf_arg,
        gps_goal_marker_node,
        static_map_odom_tf_node,
    ])
