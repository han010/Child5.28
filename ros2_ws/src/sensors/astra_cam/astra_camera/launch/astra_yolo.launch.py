import os

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python import get_package_share_directory
from launch_ros.actions import Node


def generate_launch_description():
    # 启动 Astra Mini 相机（复用已有 astra_mini.launch.py）
    astra_mini_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('astra_camera'),
                'launch',
                'astra_mini.launch.py'
            )
        )
    )

    # 启动 YOLO 障碍物检测节点（对应 yolo_ros/yolo_ros/test_msgs.py）
    yolo_node = Node(
        package='yolo_ros',
        executable='test_msgs',  # 在 setup.py 中注册的 console_script 名
        output='screen'
    )

    return LaunchDescription([
        astra_mini_launch,
        yolo_node,
    ])
