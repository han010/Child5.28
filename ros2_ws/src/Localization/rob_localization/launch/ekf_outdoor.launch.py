#!/usr/bin/env python3
"""
室外 GPS+IMU+轮程融合定位启动文件

架构:
  EKF1 (local): wheel_odom + IMU → /odometry/filtered, TF: odom→base_link
  navsat_transform: GPS + IMU + /odometry/filtered → /odometry/gps
  EKF2 (global): /odometry/filtered + /odometry/gps → /odometry/global, TF: map→odom

启动顺序:
  1. wheel_odom_node
  2. EKF1 (ekf_indoor)
  3. navsat_transform_node (延迟 3s, 等 EKF1 稳定)
  4. EKF2 (ekf_outdoor, 延迟 5s)

使用方法:
    ros2 launch rob_localization ekf_outdoor.launch.py
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction, RegisterEventHandler
from launch.event_handlers import OnProcessStart
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_path = get_package_share_directory('rob_localization')

    # ==================== 参数声明 ====================

    pose_source_arg = DeclareLaunchArgument(
        'pose_source',
        default_value='/revo/pose',
        description='位姿数据源 (PoseState)'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='使用仿真时间(bag 回放时设为 true)'
    )
    sim_time = LaunchConfiguration('use_sim_time')

    # ==================== 1. wheel_odom 节点 ====================

    wheel_odom_node = Node(
        package='rob_localization',
        executable='wheel_odom',
        name='wheel_odom',
        output='screen',
        parameters=[{
            'odom_frame': 'odom',
            'base_frame': 'base_link',
            'pose_topic': LaunchConfiguration('pose_source'),
            'wheel_odom_topic': '/wheel_odom',
            'use_sim_time': sim_time,
        }]
    )

    # ==================== 2. EKF1 (室内定位，作为局部连续 odometry) ====================

    ekf1_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[os.path.join(pkg_path, 'params', 'ekf_indoor.yaml'),
                    {'use_sim_time': sim_time}],
        remappings=[
            ('odometry/filtered', '/odometry/filtered'),
        ]
    )

    # ==================== 3. navsat_transform_node ====================

    navsat_transform_node = Node(
        package='robot_localization',
        executable='navsat_transform_node',
        name='navsat_transform',
        output='screen',
        parameters=[{
            'frequency': 20.0,
            'delay': 0.0,
            'magnetic_declination_radians': 0.0,    # 已在 revo_bridge 修正
            # 关键: Revo IMU yaw 是北参考系(0=北), navsat_transform 需要 ENU(0=东)
            # yaw_offset = π/2 ≈ 1.5708, 将北参考系转换为 ENU 参考系
            'yaw_offset': 1.5707963,
            'zero_altitude': True,                   # 忽略高度
            'broadcast_utm_transform': False,        # ENU 局部坐标系
            'publish_filtered_gps': True,
            # 使用 IMU 数据(配合 yaw_offset 做北→ENU 转换)
            # 不能用 use_odometry_yaw: True, 因为 EKF1 的 yaw 也是北参考系且无 offset
            'use_odometry_yaw': False,
            'wait_for_datum': False,
            'use_sim_time': sim_time,
        }],
        remappings=[
            ('imu/data', '/revo/imu'),
            ('gps/fix', '/gps/fix'),
            ('odometry/filtered', '/odometry/filtered'),
            ('odometry/gps', '/odometry/gps'),
        ]
    )

    # ==================== 4. EKF2 (室外定位，融合 GPS) ====================

    ekf2_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_global_node',
        namespace='ekf_global',
        output='screen',
        parameters=[os.path.join(pkg_path, 'params', 'ekf_outdoor.yaml'),
                    {'use_sim_time': sim_time}],
        remappings=[
            ('odometry/filtered', '/odometry/global'),
        ]
    )

    # ==================== GPS 静态 TF ====================
    # base_link → gps (暂时设为零偏移，后续可测实际位置)

    gps_static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='gps_static_tf',
        arguments=['0', '0', '0', '0', '0', '0', '1', 'base_link', 'gps'],
        parameters=[{'use_sim_time': sim_time}]
    )

    # ==================== 延迟启动 ====================
    # 关键: navsat 和 EKF2 需要等 EKF1 稳定

    navsat_delayed = TimerAction(
        period=3.0,  # 3 秒延迟
        actions=[navsat_transform_node]
    )

    ekf2_delayed = TimerAction(
        period=5.0,  # 5 秒延迟
        actions=[ekf2_node]
    )

    # ==================== 返回 LaunchDescription ====================

    return LaunchDescription([
        # 参数声明
        pose_source_arg,
        use_sim_time_arg,

        # 立即启动: wheel_odom + EKF1 + GPS TF
        wheel_odom_node,
        ekf1_node,
        gps_static_tf,

        # 延迟启动: navsat (3s) + EKF2 (5s)
        navsat_delayed,
        ekf2_delayed,
    ])
