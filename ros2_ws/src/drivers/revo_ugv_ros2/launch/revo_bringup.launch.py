#!/usr/bin/env python3
"""
Revo UGV 完整启动 Launch 文件

启动顺序：
1. Revo SDK 桥接节点 (keyboard_node.py)
2. 机器人模型发布 (robot_state_publisher + URDF)
3. 里程计节点 (revo_odom_node.py)
4. GNSS 节点 (revo_gnss_node.py)
5. 摄像头节点 (v4l2_camera)
6. 激光雷达节点 (rplidar_ros)
7. Foxglove 调试桥

使用方法：
    ros2 launch revo_ugv_ros2 revo_bringup.launch.py
"""

import os
import subprocess
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
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

    # IMU yaw 偏移修正参数
    yaw_offset_arg = DeclareLaunchArgument(
        'yaw_offset_deg',
        default_value='0.0',
        description='IMU yaw 偏移修正（度），使修正后车头朝真北时 yaw=0'
    )

    # 激光雷达参数
    lidar_port_arg = DeclareLaunchArgument(
        'lidar_port',
        default_value='/dev/ttyUSB0',
        description='激光雷达串口设备路径'
    )

    lidar_frame_id_arg = DeclareLaunchArgument(
        'lidar_frame_id',
        default_value='laser',
        description='激光雷达坐标系 ID'
    )

    # 摄像头参数
    camera_device_arg = DeclareLaunchArgument(
        'camera_device',
        default_value='/dev/video0',
        description='摄像头设备路径'
    )

    camera_resolution_arg = DeclareLaunchArgument(
        'camera_resolution',
        default_value='640x480',
        description='摄像头分辨率 (1920x1080, 1280x720, 640x480)',
        choices=['1920x1080', '1280x720', '640x480']
    )

    camera_frame_rate_arg = DeclareLaunchArgument(
        'camera_frame_rate',
        default_value='30.0',
        description='摄像头帧率'
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

    # 仿真时间参数
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='使用仿真时间'
    )

    # ==================== 1. Revo SDK 桥接节点 ====================

    revo_bridge_node = Node(
        package='revo_ugv_ros2',
        executable='revo_bridge',
        name='revo_bridge',
        output='screen',
        parameters=[{
            'host': LaunchConfiguration('host'),
            'client_name': LaunchConfiguration('client_name'),
            'yaw_offset_deg': LaunchConfiguration('yaw_offset_deg'),
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

    # Static TF publishers for sensors (fixed joints)
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
    # Some laser scan drivers use 'laser' frame, this links it to our 'lidar' frame
    laser_to_lidar_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='laser_to_lidar_tf',
        arguments=['0', '0', '0', '0', '0', '0', '1', 'lidar', 'laser']
    )

    # ==================== 3. 里程计节点 ====================

    revo_odom_node = Node(
        package='revo_ugv_ros2',
        executable='revo_odom',
        name='revo_odom',
        output='screen',
        parameters=[{
            'odom_frame_id': 'odom',
            'base_frame_id': 'base_link',
            'odom_publish_rate_hz': 10,
            'odom_smoothing_alpha': 0.5,
        }]
    )

    # ==================== 4. GNSS 节点 ====================

    revo_gnss_node = Node(
        package='revo_ugv_ros2',
        executable='revo_gnss',
        name='revo_gnss',
        output='screen'
    )

    # ==================== 5. 摄像头节点 ====================

    camera_node = Node(
        package='v4l2_camera',
        executable='v4l2_camera_node',
        name='v4l2_camera',  # 改名避免与camera frame冲突
        output='screen',
        parameters=[{
            'video_device': LaunchConfiguration('camera_device'),
            'image_size': [640, 480],
            'frame_rate': LaunchConfiguration('camera_frame_rate'),
            'camera_frame_id': 'camera',  # 改为与URDF一致
        }]
    )

    # ==================== 6. 激光雷达节点 ====================

    pkg_rplidar_ros = get_package_share_directory('rplidar_ros')
    rplidar_launch_file = os.path.join(pkg_rplidar_ros, 'launch', 'rplidar_a1_launch.py')

    rplidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(rplidar_launch_file),
        launch_arguments={
            'serial_port': LaunchConfiguration('lidar_port'),
            'frame_id': LaunchConfiguration('lidar_frame_id'),
        }.items()
    )

    # ==================== 7. Foxglove 调试桥 ====================

    foxglove_bridge_node = Node(
        package='foxglove_bridge',
        executable='foxglove_bridge',
        name='foxglove_bridge',
        output='screen',
        parameters=[{
            'port': 8765,
            'address': '0.0.0.0',
            'log_unavailable_types': False,  # 不记录不可用类型的警告
            'max_msg_length': 10000000,      # 10MB 最大消息长度
        }]
    )

    # ==================== 返回 LaunchDescription ====================

    return LaunchDescription([
        # 参数声明
        host_arg,
        client_name_arg,
        yaw_offset_arg,
        lidar_port_arg,
        lidar_frame_id_arg,
        camera_device_arg,
        camera_resolution_arg,
        camera_frame_rate_arg,
        use_sim_time_arg,

        # 节点启动（按顺序）
        revo_bridge_node,
        robot_state_publisher_node,
        joint_state_publisher_node,
        camera_static_tf,  # 添加相机静态TF
        lidar_static_tf,   # 添加雷达静态TF
        laser_to_lidar_tf, # laser -> lidar 兼容性TF
        revo_odom_node,
        revo_gnss_node,
        camera_node,
        rplidar_launch,
        foxglove_bridge_node,
    ])
