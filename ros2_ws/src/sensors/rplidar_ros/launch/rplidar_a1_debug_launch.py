#!/usr/bin/env python3
# RPLIDAR A1 调试启动文件 - 禁用scan_mode参数使用默认值

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node


def generate_launch_description():
    # RPLIDAR A1 使用默认扫描模式（不指定scan_mode）
    # 这样可以让SDK自动选择合适的模式
    return LaunchDescription([
        Node(
            package='rplidar_ros',
            executable='rplidar_composition',
            name='rplidar_node',
            parameters=[{
                'channel_type': 'serial',
                'serial_port': '/dev/ttyUSB0',
                'serial_baudrate': 115200,  # A1/A2使用115200
                'frame_id': 'laser',
                'inverted': False,
                'angle_compensate': True,
                # 不设置scan_mode，让SDK使用默认模式
                'scan_frequency': 10.0,
            }],
            output='screen',
            emulate_tty=True,
        ),
    ])
