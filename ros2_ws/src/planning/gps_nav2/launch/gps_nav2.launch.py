#!/usr/bin/env python3
"""
GPS导航启动文件 - 使用Nav2进行室外GPS导航

启动顺序:
1. robot_localization (EKF) - 融合GPS+IMU+轮速计
2. Nav2导航栈 - 路径规划和控制
3. gps_nav_goal节点 - GPS目标点接收和坐标转换

使用方法:
# 启动GPS导航
ros2 launch gps_nav2 gps_nav2.launch.py

# 发送单个GPS目标点
ros2 service call /set_gps_goal gps_nav2/srv/GPSGoal \
  "{latitude: 30.2551, longitude: 120.2941}"

# 发送多点GPS航点
ros2 service call /set_gps_waypoints gps_nav2/srv/GPSWaypointNav \
  "{waypoints: [{latitude: 30.2551, longitude: 120.2941}, \
                {latitude: 30.2552, longitude: 120.2942}], \
    loop: false}"
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    # 获取包路径
    pkg_gps_nav2 = get_package_share_directory('gps_nav2')

    # ==================== 声明参数 ====================

    # GPS/UTM参数
    utm_zone_arg = DeclareLaunchArgument(
        'utm_zone',
        default_value='51N',
        description='UTM分区 (中国东部: 51N)'
    )

    # 导航参数
    use_nav2_waypoints_arg = DeclareLaunchArgument(
        'use_nav2_waypoints',
        default_value='true',
        description='使用Nav2 Waypoint Follower'
    )

    nav2_server_timeout_arg = DeclareLaunchArgument(
        'nav2_server_timeout',
        default_value='10.0',
        description='Nav2服务器超时(秒)'
    )

    gps_tolerance_arg = DeclareLaunchArgument(
        'gps_tolerance',
        default_value='2.0',
        description='GPS到达容差(米)'
    )

    # Nav2配置文件路径
    nav2_params_file_arg = DeclareLaunchArgument(
        'nav2_params_file',
        default_value=PathJoinSubstitution([
            pkg_gps_nav2, 'config', 'nav2', 'nav2_params_gps.yaml'
        ]),
        description='Nav2配置文件路径'
    )

    # EKF配置文件路径
    ekf_config_file_arg = DeclareLaunchArgument(
        'ekf_config_file',
        default_value=PathJoinSubstitution([
            pkg_gps_nav2, 'config', 'ekf.yaml'
        ]),
        description='EKF配置文件路径'
    )

    # 是否使用仿真时间
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='使用仿真时间'
    )

    # 是否自动启动
    autostart_arg = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='自动启动导航'
    )

    # ==================== robot_localization节点 ====================

    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[LaunchConfiguration('ekf_config_file'), {
            'use_sim_time': LaunchConfiguration('use_sim_time'),
        }],
        remappings=[
            ('/odometry/gps', '/odometry/gps'),  # 融合后的里程计输出
        ]
    )

    # ==================== Nav2导航栈 ====================
    # 使用nav2_bringup的navigation_launch.py启动完整导航栈

    from launch.actions import IncludeLaunchDescription
    from launch.launch_description_sources import PythonLaunchDescriptionSource

    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')

    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav2_bringup, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'autostart': LaunchConfiguration('autostart'),
            'params_file': LaunchConfiguration('nav2_params_file'),
        }.items()
    )

    # ==================== GPS导航目标节点 ====================

    gps_nav_goal_node = Node(
        package='gps_nav2',
        executable='gps_nav_goal',
        name='gps_nav_goal_node',
        output='screen',
        parameters=[{
            'utm_zone': LaunchConfiguration('utm_zone'),
            'use_nav2_waypoints': LaunchConfiguration('use_nav2_waypoints'),
            'nav2_server_timeout': LaunchConfiguration('nav2_server_timeout'),
            'gps_tolerance': LaunchConfiguration('gps_tolerance'),
            'publish_rate': 5.0,
        }]
    )

    # ==================== 启动顺序 ====================
    # 1. 首先启动robot_localization
    # 2. 然后启动Nav2
    # 3. 最后启动GPS导航目标节点

    return LaunchDescription([
        # 参数声明
        utm_zone_arg,
        use_nav2_waypoints_arg,
        nav2_server_timeout_arg,
        gps_tolerance_arg,
        nav2_params_file_arg,
        ekf_config_file_arg,
        use_sim_time_arg,
        autostart_arg,

        # 节点启动 (按顺序)
        ekf_node,

        # 延迟启动Nav2 (等待EKF初始化)
        TimerAction(
            period=2.0,
            actions=[nav2_bringup]
        ),

        # 延迟启动GPS导航节点 (等待Nav2就绪)
        TimerAction(
            period=5.0,
            actions=[gps_nav_goal_node]
        ),
    ])
