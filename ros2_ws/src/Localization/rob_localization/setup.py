from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'rob_localization'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'params'), glob('params/*.yaml')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='orin',
    maintainer_email='orin@agri-ugv.local',
    description='Robot localization configuration for Revo UGV',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'wheel_odom = rob_localization_pkg.wheel_odom_node:main',
            'gps_to_odom = rob_localization_pkg.gps_to_odom_node:main',
            'cmd_vel_relay = rob_localization_pkg.cmd_vel_relay:main',
        ],
    },
)
