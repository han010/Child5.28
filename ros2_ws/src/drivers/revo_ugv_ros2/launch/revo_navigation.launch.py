"""
Revo UGM 室内导航启动文件

功能：
- 启动 map_server (加载 slam_toolbox 创建的地图)
- 启动 AMCL 定位
- 启动 Nav2 导航栈
- 配置 costmap、planner、controller

使用方法：
    ros2 launch revo_ugv_ros2 revo_navigation.launch.py

依赖：
- 里程计: /odom
- 激光雷达: /scan
- 速度控制: /revo/cmd_vel
- 地图文件: maps/map.yaml
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.conditions import IfCondition


def generate_launch_description():
    # 获取包路径
    revo_ugv_ros2_dir = get_package_share_directory('revo_ugv_ros2')
    nav2_dir = get_package_share_directory('nav2_bringup')

    # 配置文件路径
    nav2_params_file = os.path.join(revo_ugv_ros2_dir, 'config', 'nav2_params.yaml')
    map_file = os.path.join(revo_ugv_ros2_dir, 'maps', '2a416_map.yaml')

    # Launch 参数
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    map_file_arg = LaunchConfiguration('map')
    params_file_arg = LaunchConfiguration('params_file')

    # 声明 launch 参数
    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true')

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically startup the nav2 stack')

    declare_map_file_cmd = DeclareLaunchArgument(
        'map',
        default_value=map_file,
        description='Full path to map file to load')

    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value=nav2_params_file,
        description='Full path to nav2 params file')

    # 设置环境变量
    set_env_var = SetEnvironmentVariable('RCUTILS_LOGGING_BUFFERED_STREAM', '1')

    # ========== 节点定义 ==========

    # Map Server
    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[
            {'yaml_filename': map_file_arg},
            {'use_sim_time': use_sim_time}
        ]
    )

    # AMCL (定位)
    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[params_file_arg],
        condition=IfCondition(autostart)
    )

    # Lifecycle Manager (管理 map_server 和 amcl 的生命周期)
    lifecycle_manager_map_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_map',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'autostart': autostart},
            {'node_names': ['map_server', 'amcl']}
        ]
    )

    # Planner Server (全局路径规划)
    planner_server_node = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[params_file_arg],
        condition=IfCondition(autostart)
    )

    # Controller Server (局部路径规划 + 控制)
    controller_server_node = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[params_file_arg],
        condition=IfCondition(autostart)
    )

    # Behavior Server (恢复行为)
    behavior_server_node = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[params_file_arg],
        condition=IfCondition(autostart)
    )

    # BT Navigator (行为树导航)
    bt_navigator_node = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[params_file_arg],
        condition=IfCondition(autostart)
    )

    # Waypoint Follower (航点跟随)
    waypoint_follower_node = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        name='waypoint_follower',
        output='screen',
        parameters=[params_file_arg],
        condition=IfCondition(autostart)
    )

    # Lifecycle Manager (管理导航栈)
    lifecycle_manager_nav_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'autostart': autostart},
            {'node_names': [
                'planner_server',
                'controller_server',
                'behavior_server',
                'bt_navigator',
                'waypoint_follower'
            ]}
        ]
    )

    # RViz2 (可选，用于可视化)
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', os.path.join(nav2_dir, 'nav2_default_view.rviz')],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(LaunchConfiguration('rviz'))
    )

    declare_rviz_cmd = DeclareLaunchArgument(
        'rviz',
        default_value='true',
        description='Open RViz2 automatically')

    # 创建 LaunchDescription
    ld = LaunchDescription()

    # 添加声明
    ld.add_action(set_env_var)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_map_file_cmd)
    ld.add_action(declare_params_file_cmd)
    ld.add_action(declare_rviz_cmd)

    # 添加节点
    ld.add_action(map_server_node)
    ld.add_action(amcl_node)
    ld.add_action(lifecycle_manager_map_node)
    ld.add_action(planner_server_node)
    ld.add_action(controller_server_node)
    ld.add_action(behavior_server_node)
    ld.add_action(bt_navigator_node)
    ld.add_action(waypoint_follower_node)
    ld.add_action(lifecycle_manager_nav_node)
    ld.add_action(rviz_node)

    return ld
