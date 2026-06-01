import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    port_name = LaunchConfiguration('port_name')
    serial_port = LaunchConfiguration('serial_port')
    serial_baudrate = LaunchConfiguration('serial_baudrate')
    lidar_frame = LaunchConfiguration('lidar_frame')
    slam_params = os.path.join(
        get_package_share_directory('hunter_base'),
        'config',
        'slam_params.yaml'
    )
    slam_qos = os.path.join(
        get_package_share_directory('hunter_base'),
        'config',
        'slam_qos.yaml'
    )

    urdf_path = os.path.join(
        get_package_share_directory('hunter_base'),
        'urdf',
        'hunter.urdf'
    )

    with open(urdf_path, 'r') as urdf_file:
        robot_description_content = urdf_file.read()

    robot_state_pub = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'robot_description': robot_description_content
        }]
    )

    hunter_base_node = Node(
        package='hunter_base',
        executable='hunter_base_node',
        output='screen',
        parameters=[{
            'port_name': port_name
        }]
    )

    lidar_node = Node(
        package='rplidar_ros',
        executable='rplidar_composition',
        name='rplidar_composition',
        output='screen',
        parameters=[{
            'serial_port': serial_port,
            'serial_baudrate': serial_baudrate,
            'frame_id': lidar_frame
        }]
    )

    tf_echo = Node(
        package='tf2_ros',
        executable='tf2_echo',
        name='tf2_echo_odom_base',
        output='screen',
        arguments=['odom', 'base_link']
    )

    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='sync_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            slam_params,
            slam_qos,
            {'use_sim_time': use_sim_time}
        ]
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation time'),
        DeclareLaunchArgument(
            'port_name',
            default_value='can0',
            description='CAN bus name for hunter_base'),
        DeclareLaunchArgument(
            'serial_port',
            default_value='/dev/ttyUSB0',
            description='RPLIDAR serial port'),
        DeclareLaunchArgument(
            'serial_baudrate',
            default_value='115200',
            description='RPLIDAR baudrate'),
        DeclareLaunchArgument(
            'lidar_frame',
            default_value='laser_link',
            description='Frame id for laser scan'),
        robot_state_pub,
        hunter_base_node,
        lidar_node,
        slam_toolbox_node,
        tf_echo
    ])
