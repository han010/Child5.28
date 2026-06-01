from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'revo_ugv_ros2'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/urdf', ['urdf/revo_ugv.urdf.xacro']),
        ('share/' + package_name + '/config', glob('config/**/*.yaml') + glob('config/*.json') + glob('config/nav2/*.yaml')),
        ('share/' + package_name + '/maps', glob('maps/*.yaml') + glob('maps/*.pgm')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='orin',
    maintainer_email='937333878@qq.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'revo_bridge = revo_ugv_ros2.revo_bridge_node:main',
            'revo_odom = revo_ugv_ros2.revo_odom_node:main',
            'revo_teleop_keyboard = revo_ugv_ros2.revo_teleop_keyboard:main',
            'revo_gnss = revo_ugv_ros2.revo_gnss_node:main',
            'gps_waypoint_nav = revo_ugv_ros2.gps_waypoint_nav:main',
            'gps_waypoint_nav_odom = revo_ugv_ros2.gps_waypoint_nav_odom:main',
        ],
    },
)
