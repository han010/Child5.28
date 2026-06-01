#!/usr/bin/env python3
"""
Revo UGV 底盘启动 Launch 文件

此文件仅启动 Revo SDK 桥接节点，用于与底盘通信。
由于底盘节点可能需要频繁重启，因此单独分离出来。

启动内容：
- Revo SDK 桥接节点 (keyboard_node.py)
- 机器人模型发布 (robot_state_publisher + URDF)
- 静态 TF 发布

使用方法：
    ros2 launch revo_ugv_ros2 revo_chassis.launch.py

可选参数：
    host: Revo 底盘 IP 地址 (默认: 192.168.234.1)
    client_name: 客户端名称 (默认: RevoUGV)
"""

import os
import subprocess
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # 获取包路径
    pkg_revo_ugv_ros2 = get_package_share_directory('revo_ugv_ros2')

    # ==================== 声明 launch 参数 ====================

    # Revo SDK 连接参数
    host_arg = DeclareLaunchArgument(
        'host',
        default_value='192.168.234.1',
        description='Revo 底盘 IP 地址'
    )

    client_name_arg = DeclareLaunchArgument(
        'client_name',
        default_value='RevoUGV',
        description='客户端名称'
    )

    # 仿真时间参数
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='使用仿真时间'
    )

    # URDF 文件路径
    urdf_file = os.path.join(pkg_revo_ugv_ros2, 'urdf', 'revo_ugv.urdf.xacro')

    # 使用 xacro 处理 URDF 文件
    try:
        process = subprocess.Popen(['xacro', urdf_file], stdout=subprocess.PIPE)
        robot_description, _ = process.communicate()
        robot_description = robot_description.decode('utf-8')
    except Exception as e:
        raise RuntimeError(f'Failed to process xacro file: {e}')

    # ==================== 1. Revo SDK 桥接节点 ====================

    revo_bridge_node = Node(
        package='revo_ugv_ros2',
        executable='revo_bridge',
        name='revo_bridge',
        output='screen',
        parameters=[{
            'host': LaunchConfiguration('host'),
            'client_name': LaunchConfiguration('client_name'),
        }]
    )

    # ==================== 2. 机器人模型发布 ====================

    # robot_state_publisher 节点
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': LaunchConfiguration('use_sim_time')
        }]
    )

    # joint_state_publisher 节点
    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time')
        }]
    )

    # ==================== 3. 静态 TF 发布 ====================

    # Camera: base_link -> camera at (0.4, 0.2, 0.16)
    camera_static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='camera_static_tf',
        arguments=['--x', '0.4', '--y', '0.2', '--z', '0.16',
                   '--qx', '0', '--qy', '0', '--qz', '0', '--qw', '1',
                   '--frame-id', 'base_link', '--child-frame-id', 'camera']
    )

    # LiDAR: base_link -> lidar at (0.4, 0, 0.2)
    lidar_static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='lidar_static_tf',
        arguments=['--x', '0.4', '--y', '0', '--z', '0.2',
                   '--qx', '0', '--qy', '0', '--qz', '0', '--qw', '1',
                   '--frame-id', 'base_link', '--child-frame-id', 'lidar']
    )

    # Additional TF: laser -> lidar (identity transform for compatibility)
    laser_to_lidar_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='laser_to_lidar_tf',
        arguments=['0', '0', '0', '0', '0', '0', '1', 'lidar', 'laser']
    )

    # ==================== 返回 LaunchDescription ====================

    return LaunchDescription([
        # 参数声明
        host_arg,
        client_name_arg,
        use_sim_time_arg,

        # 节点启动
        revo_bridge_node,
        robot_state_publisher_node,
        joint_state_publisher_node,
        camera_static_tf,
        lidar_static_tf,
        laser_to_lidar_tf,
    ])
