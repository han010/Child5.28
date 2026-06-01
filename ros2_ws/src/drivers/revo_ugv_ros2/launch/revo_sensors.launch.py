#!/usr/bin/env python3
"""
Revo UGV 传感器启动 Launch 文件

此文件启动除底盘桥接之外的所有节点，包括：
- 里程计节点 (revo_odom_node.py)
- GNSS 节点 (revo_gnss_node.py)
- 摄像头节点 (v4l2_camera)
- 激光雷达节点 (rplidar_ros)
- Foxglove 调试桥

使用方法：
    ros2 launch revo_ugv_ros2 revo_sensors.launch.py

注意：
    启动此文件前，请先启动底盘节点：
    ros2 launch revo_ugv_ros2 revo_chassis.launch.py
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # ==================== 声明 launch 参数 ====================

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

    # 里程计参数
    odom_publish_rate_arg = DeclareLaunchArgument(
        'odom_publish_rate_hz',
        default_value='10',
        description='里程计发布频率 (Hz)'
    )

    odom_smoothing_alpha_arg = DeclareLaunchArgument(
        'odom_smoothing_alpha',
        default_value='0.5',
        description='里程计平滑系数 (0.0-1.0, 越小越平滑)'
    )

    # Foxglove 参数
    foxglove_port_arg = DeclareLaunchArgument(
        'foxglove_port',
        default_value='8765',
        description='Foxglove Bridge 端口'
    )

    # 仿真时间参数
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='使用仿真时间'
    )

    # ==================== 1. 里程计节点 ====================

    revo_odom_node = Node(
        package='revo_ugv_ros2',
        executable='revo_odom',
        name='revo_odom',
        output='screen',
        parameters=[{
            'odom_frame_id': 'odom',
            'base_frame_id': 'base_link',
            'odom_publish_rate_hz': LaunchConfiguration('odom_publish_rate_hz'),
            'odom_smoothing_alpha': LaunchConfiguration('odom_smoothing_alpha'),
        }]
    )

    # ==================== 2. GNSS 节点 ====================

    revo_gnss_node = Node(
        package='revo_ugv_ros2',
        executable='revo_gnss',
        name='revo_gnss',
        output='screen'
    )

    # ==================== 3. 摄像头节点 ====================

    camera_node = Node(
        package='v4l2_camera',
        executable='v4l2_camera_node',
        name='v4l2_camera',
        output='screen',
        parameters=[{
            'video_device': LaunchConfiguration('camera_device'),
            'image_size': [640, 480],
            'frame_rate': LaunchConfiguration('camera_frame_rate'),
            'camera_frame_id': 'camera',
        }]
    )

    # ==================== 4. 激光雷达节点 ====================

    # 导入 IncludeLaunchDescription
    from launch.actions import IncludeLaunchDescription
    from launch.launch_description_sources import PythonLaunchDescriptionSource

    # 尝试获取 rplidar_ros 包的 launch 文件路径
    rplidar_launch = None
    try:
        pkg_rplidar_ros = get_package_share_directory('rplidar_ros')
        rplidar_launch_file = os.path.join(pkg_rplidar_ros, 'launch', 'rplidar_a1_launch.py')

        # 检查launch文件是否存在
        if os.path.exists(rplidar_launch_file):
            # 使用 IncludeLaunchDescription 启动激光雷达
            rplidar_launch = IncludeLaunchDescription(
                PythonLaunchDescriptionSource(rplidar_launch_file),
                launch_arguments={
                    'serial_port': LaunchConfiguration('lidar_port'),
                    'frame_id': LaunchConfiguration('lidar_frame_id'),
                }.items()
            )
    except Exception:
        pass

    # 如果无法使用launch文件，直接启动节点
    if rplidar_launch is None:
        rplidar_launch = Node(
            package='rplidar_ros',
            executable='rplidar_composition',
            name='rplidar_node',
            output='screen',
            parameters=[{
                'serial_port': LaunchConfiguration('lidar_port'),
                'frame_id': LaunchConfiguration('lidar_frame_id'),
                'angle_compensate': True,
                'scan_mode': 'Standard',
            }]
        )

    # ==================== 5. Foxglove 调试桥 ====================

    foxglove_bridge_node = Node(
        package='foxglove_bridge',
        executable='foxglove_bridge',
        name='foxglove_bridge',
        output='screen',
        parameters=[{
            'port': LaunchConfiguration('foxglove_port'),
            'address': '0.0.0.0',
            'log_unavailable_types': False,  # 不记录不可用类型的警告
            'max_msg_length': 10000000,      # 10MB 最大消息长度
        }]
    )

    # ==================== 返回 LaunchDescription ====================

    return LaunchDescription([
        # 参数声明
        camera_device_arg,
        camera_resolution_arg,
        camera_frame_rate_arg,
        lidar_port_arg,
        lidar_frame_id_arg,
        odom_publish_rate_arg,
        odom_smoothing_alpha_arg,
        foxglove_port_arg,
        use_sim_time_arg,

        # 节点启动
        #revo_odom_node,
        revo_gnss_node,
        camera_node,
        rplidar_launch,
        foxglove_bridge_node,
    ])
