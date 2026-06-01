from setuptools import setup, find_packages
from glob import glob
import os

package_name = 'gps_goal_tool'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='orin',
    maintainer_email='937333878@qq.com',
    description='GPS目标点工具 - GPS坐标转本地坐标并在rviz2中显示',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'gps_goal_marker = gps_goal_tool.gps_goal_marker:main',
            'static_map_odom_tf = gps_goal_tool.static_map_odom_tf:main',
        ],
    },
)
