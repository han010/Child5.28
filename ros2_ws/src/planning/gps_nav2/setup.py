from setuptools import setup
from glob import glob
import os

package_name = 'gps_nav2'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/**/*.yaml') + glob('config/*.yaml')),
        ('share/' + package_name + '/config/nav2', glob('config/nav2/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='orin',
    maintainer_email='937333878@qq.com',
    description='GPS navigation package for agricultural UGV using Nav2',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'gps_nav_goal = gps_nav2.gps_nav_goal:main',
        ],
    },
)
