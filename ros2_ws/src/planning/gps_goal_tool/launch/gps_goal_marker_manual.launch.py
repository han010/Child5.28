"""
GPS目标点标记节点 - 手动模式Launch文件

使用场景：
- 没有真实GPS设备，仅用于测试
- 或者想手动指定GPS原点和机器人朝向

用法:
ros2 launch gps_goal_tool gps_goal_marker_manual.launch.py
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # 声明参数
    origin_lat_arg = DeclareLaunchArgument(
        'origin_latitude',
        default_value='30.2552028',
        description='GPS原点纬度 (机器人启动位置)'
    )
    origin_lon_arg = DeclareLaunchArgument(
        'origin_longitude',
        default_value='120.2941317',
        description='GPS原点经度 (机器人启动位置)'
    )
    yaw_arg = DeclareLaunchArgument(
        'manual_yaw_deg',
        default_value='0.0',
        description='机器人朝向角 (度，正北为0，顺时针为正)'
    )
    utm_zone_arg = DeclareLaunchArgument(
        'utm_zone',
        default_value='51N',
        description='UTM分区 (中国东部: 51N)'
    )

    # GPS目标标记节点
    gps_goal_marker_node = Node(
        package='gps_goal_tool',
        executable='gps_goal_marker',
        name='gps_goal_marker_node',
        output='screen',
        parameters=[{
            'utm_zone': LaunchConfiguration('utm_zone'),
            'map_frame': 'map',
            'marker_scale': 1.0,
            'auto_send_nav2_goal': True,
            'origin_mode': 'manual',  # 手动模式
            'origin_latitude': LaunchConfiguration('origin_latitude'),
            'origin_longitude': LaunchConfiguration('origin_longitude'),
            'use_manual_yaw': True,
            'manual_yaw_deg': LaunchConfiguration('manual_yaw_deg'),
        }]
    )

    return LaunchDescription([
        origin_lat_arg,
        origin_lon_arg,
        yaw_arg,
        utm_zone_arg,
        gps_goal_marker_node,
    ])
