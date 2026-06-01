# CLAUDE.md

请始终使用简体中文与我对话，并在回答时保持专业、简洁。

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 快速链接

- `docs/新人入门指南.md` - 快速入门指南
- `docs/代码阅读指引.md` - 代码阅读顺序指引
- `docs/ROS_TOPICS_API.md` - 完整的ROS话题接口文档
- `docs/ROS_TOPICS_QUICK_REF.md` - ROS话题快速参考
- `docs/GIT_WORKFLOW.md` - Git Flow分支管理策略

## 项目概述

基于 ROS2 的农业无人车(UGV)项目，支持两个机器人平台：

- **XAG Revo R100/R200**: 通过 UDP 协议控制的农业机器人平台（当前主力）
- **Agilex Hunter SE**: 通过 CAN 总线控制的移动机器人平台

### 工作空间结构

```
ros2_ws/src/
├── drivers/                # 机器人驱动层
│   ├── revo_ugv_ros2/      # XAG Revo ROS2封装 (Python)
│   ├── hunter_ros2/        # Hunter SE ROS2封装 (C++)
│   ├── revo_msgs/          # 自定义Revo消息
│   └── ugv_sdk/            # Agilex UGV SDK (C++库)
├── Localization/           # 传感器融合定位
│   └── rob_localization/   # EKF定位 (wheel_odom + IMU)
├── sensors/                # 传感器驱动
│   ├── rplidar_ros/        # RPLIDAR A1激光雷达
│   ├── OrbbecSDK_ROS2/     # Orbbec深度相机SDK
│   ├── astra_cam/          # Orbbec Astra相机驱动
│   ├── serial_ros2/        # 串口通信
│   ├── wheeltec_gps/       # GPS/NMEA驱动
│   ├── wheeltec_radar/     # 毫米波雷达
│   └── perception/         # YOLOv8目标检测（开发中）
├── planning/               # 导航与规划
│   ├── gps_nav2/           # GPS导航 (Nav2)
│   └── gps_goal_tool/      # GPS航点工具
└── revosdk/                # Revo Python SDK
```

## 构建和设置

**colcon build 必须在 `ros2_ws/` 目录下执行：**

```bash
cd /home/orin/Workspace/agri_ugv/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

构建特定包：
```bash
colcon build --packages-select <package_name>
```

加载工作空间（添加到 ~/.bashrc）：
```bash
source /home/orin/Workspace/agri_ugv/ros2_ws/install/setup.bash
```

### CAN总线设置 (Hunter SE)

首次设置：
```bash
sudo modprobe gs_usb
cd ros2_ws/src/drivers/ugv_sdk/scripts/ && sudo bash setup_can2usb.bash
```

每次断电后启动CAN：
```bash
cd ros2_ws/src/drivers/ugv_sdk/scripts/ && sudo bash bringup_can2usb_500k.bash
```

## 启动机器人

### XAG Revo (UDP控制)

启动所有Revo节点：
```bash
ros2 launch revo_ugv_ros2 revo_bringup.launch.py
```

启动内容：SDK桥接(192.168.234.1:10151)、URDF、里程计、GNSS、摄像头、Foxglove桥

键盘遥控：
```bash
ros2 run revo_ugv_ros2 revo_teleop_keyboard
```

单独启动节点：
```bash
ros2 run revo_ugv_ros2 revo_bridge      # SDK桥接
ros2 run revo_ugv_ros2 revo_odom        # 里程计
ros2 run revo_ugv_ros2 revo_gnss        # GNSS
```

### Hunter SE (CAN控制)

```bash
ros2 launch hunter_base hunter_base.launch.py
```

参数：`port_name`(默认can0)、`odom_frame`(默认odom)、`base_frame`(默认base_link)、`simulated_robot`(仿真设true)

## 导航

### GPS航点导航

```bash
ros2 launch gps_nav2 gps_nav2.launch.py        # GPS导航栈
ros2 launch gps_goal_tool gps_goal_tool.launch.py  # GPS航点工具
```

### Revo室内导航

```bash
ros2 launch revo_ugv_ros2 revo_navigation.launch.py
ros2 run revo_ugv_ros2 indoor_nav_test          # 导航测试
```

配置文件：`drivers/revo_ugv_ros2/config/nav2/nav2_params.yaml`

### SLAM建图

Hunter：
```bash
ros2 launch hunter_base hunter_slam.launch.py
```

Revo：使用 `slam_toolbox` 在线建图
```bash
ros2 launch revo_ugv_ros2 revo_bringup.launch.py  # 启动Revo
ros2 launch rplidar_ros rplidar_a1.launch.py       # 启动雷达
# 然后运行 slam_toolbox
```

### 雷达点云过滤

`rplidar_ros` 包中集成了 `laser_filters`，过滤车身遮挡产生的无效回波：

配置文件：`sensors/rplidar_ros/config/laser_filter.yaml`

- **角度过滤**：保留 -150° ~ +150°，屏蔽正后方 ±30° 盲区
- **距离过滤**：去除 0.3m 以内的点（车身自身回波）

数据流：`rplidar_node → /scan → laser_filter_node → /scan_filtered → Nav2 costmap`

**注意**：Nav2 costmap 需订阅 `/scan_filtered`；SLAM 建图可订阅原始 `/scan`。

## EKF定位

融合轮速里程计 + IMU 的EKF定位，适用于室内无GPS环境。

**依赖**：`robot_localization` ROS2包（需单独安装）

```bash
# 前置：revo_bridge 必须运行（提供 /revo/pose 和 /revo/imu）
ros2 launch rob_localization ekf_indoor.launch.py
```

数据流：
1. `revo_bridge_node` → `/revo/pose` + `/revo/imu`
2. `wheel_odom_node` → `/wheel_odom` (仅含twist)
3. `ekf_filter_node` → `/odometry/filtered` + TF `odom→base_link`

配置文件：`Localization/rob_localization/params/ekf_indoor.yaml`

EKF融合：`odom0: /wheel_odom`(轮速vx)、`imu0: /revo/imu`(yaw+vyaw)、2D模式

参考文档：`Localization/rob_localization/docs/robot_localization_guide.md`

**重要**：`robot_localization` 3.5.x 的 YAML 解析bug — `initial_estimate_covariance` 必须提供完整15×15矩阵。详见 `docs/troubleshooting_ekf_nan.md`。

## 关键话题和坐标系

### Revo
- `/revo/cmd_vel` - 速度命令 (geometry_msgs/Twist)
- `/odom` - 里程计 (nav_msgs/Odometry)
- `/revo/pose` - 底盘位姿数据
- `/revo/imu` - IMU数据 (sensor_msgs/Imu)
- `/revo/system_status` - 系统状态
- `/revo/battery` - 电池数据

### EKF定位
- `/wheel_odom` - 轮速里程计（仅twist）
- `/odometry/filtered` - EKF融合里程计

坐标系：`base_footprint` → `base_link` → `camera`/`lidar`

### Hunter
- `/cmd_vel` - 速度命令
- `/odom` - 里程计
- `/ugv_status` - 机器人状态

坐标系：`odom` → `base_link`

### YOLO目标检测
- `/yolo_obstacles` - 检测到的障碍物
- `/image_raw` - 摄像头输入
- `/yolo_visualization` - 调试图像

详见 `docs/ROS_TOPICS_API.md`

## 架构说明

### 系统架构（四层）

1. **硬件抽象层**：SDK库(revosdk, ugv_sdk)直接与机器人硬件通信
2. **ROS2适配层**：桥接节点将SDK数据转换为ROS话题/服务
3. **定位层**：EKF传感器融合（轮速计+IMU），用于室内精确定位
4. **应用层**：导航、SLAM、目标检测等

### Revo SDK协议

- UDP协议，默认IP 192.168.234.1:10151
- 二进制协议（小端序）
- 连接流程：`connect()` → `register()` → `acquire_control()` → 发送命令
- 控制频率最大50Hz

**缓存发布模式**：SDK回调高频缓存数据，定时器按配置频率(如10Hz)发布到ROS话题。

**速度单位**：线速度 m/s×100，角速度 rad/s×1000

**里程计**：直接使用IMU yaw（不受打滑影响）+ 轮速线速度位置积分 + 可配置平滑滤波器

**坐标转换**：Revo yaw顺时针为正，ROS逆时针为正，取反处理。

Python SDK位置：`ros2_ws/src/revosdk/xa_revosdk_ugv/`

### Hunter SDK协议

- CAN总线通信，波特率500K
- 协议V2，内置自行车模型

C++ SDK位置：`ros2_ws/src/drivers/ugv_sdk/`

### Revo ROS2包结构 (revo_ugv_ros2)

Python包，入口点(setup.py)：
- `revo_bridge` - SDK桥接
- `revo_odom` - 里程计(带平滑)
- `revo_gnss` - GNSS数据转换
- `revo_teleop_keyboard` - 键盘遥控

配置文件：`config/revo_bridge_config.json`、`config/nav2/`、`config/slam_*.yaml`

Launch文件（5个）：
- `revo_bringup.launch.py` - 主启动（底盘+传感器+桥接）
- `revo_chassis.launch.py` - 仅底盘
- `revo_sensors.launch.py` - 仅传感器
- `revo_navigation.launch.py` - 室内导航
- `gps_waypoint_nav.launch.py` - GPS航点导航

### 定位包结构 (rob_localization)

Python包，依赖 `robot_localization`：
- 入口：`wheel_odom` - 将PoseState转为标准Odometry(仅twist)
- Launch：`ekf_indoor.launch.py` - wheel_odom + EKF
- 配置：`params/ekf_indoor.yaml`、`params/ekf_reference.yaml`

### Hunter ROS2包结构 (hunter_ros2)

C++包：
- `hunter_base_node` - 主节点
- 源码：`hunter_base_ros.cpp`、`hunter_base_node.cpp`、`bicycle_model.cpp`
- 构建系统：ament_cmake，链接 ugv_sdk + ascent 库

### 自定义消息

**revo_msgs**：`PoseState.msg`、`SystemStatus.msg`、`BatteryStatus.msg`
**hunter_msgs**：`SystemMessage.msg`
**gps_nav2**：`GPSGoal.srv`、`GPSWaypointNav.srv`、`GPSNavControl.srv`、`GPSStatus.msg`

### 坐标系约定

**ROS机体坐标系 (REP-103)**：右手系，X+前方，Y+左侧，Z+上方，Yaw左转正(逆时针)
**ROS地图坐标系 (REP-105)**：ENU，X+东，Y+北，Z+上

**Revo SDK IMU**：Yaw顺时针为正，真北为0弧度，int16存储(1/1000弧度)

**Revo→ROS坐标转换**：
- IMU Yaw取反：`imu_yaw = -float(pose.yaw) / 1000.0`
- 角速度取反：`ang = -float(msg.angular.z)` → `sdk_angular = int(ang * 1000)`

**里程计坐标系层次**：
```
odom → base_footprint → base_link → camera/lidar
```

**GPS→ROS Map**：ENU近似，原点为首次GPS定位位置，X+东(Y+北)。适合小范围应用。

**Revo SDK数据单位**：
- 经纬度：degrees × 10⁷ (int32)
- 海拔：meters × 10 (int16)
- 姿态角：radians × 1000 (int16)
- 线速度：m/s × 100 (int16)
- 角速度：rad/s × 1000 (int16)

**TF静态变换**：
- `base_link → camera`: (0.4, 0.2, 0.16)
- `base_link → lidar`: (0.4, 0, 0.2)

## 常见问题

### Hunter不移动
1. `ifconfig can0` 检查CAN接口
2. `candump can0` 检查CAN通信
3. 确保急停已释放
4. 遥控器在SDK/PC模式

### Revo无法连接
1. `ping 192.168.234.1` 检查网络
2. `ros2 node list | grep revo` 确认节点运行
3. 检查UDP端口

### TF错误
- Revo基座坐标系为 `base_footprint`

## 开发

### Git工作流

项目使用 Git Flow，详见 `docs/GIT_WORKFLOW.md`：

- `main` - 稳定发布
- `develop` - 当前开发（默认）

### 添加新Revo节点
1. 在 `drivers/revo_ugv_ros2/revo_ugv_ros2/` 创建Python文件
2. 在 `setup.py` 的 `console_scripts` 添加入口点
3. `colcon build --packages-select revo_ugv_ros2`

### 添加新定位节点
1. 在 `Localization/rob_localization/rob_localization_pkg/` 创建Python文件
2. 在 `setup.py` 添加入口点
3. `colcon build --packages-select rob_localization`

### 修改Hunter节点
1. 编辑 `drivers/hunter_ros2/hunter_base/src/` 中的C++源码
2. `colcon build --packages-select hunter_base`

### URDF文件
- Revo: `drivers/revo_ugv_ros2/urdf/revo_ugv.urdf.xacro`
- Hunter: `drivers/hunter_ros2/hunter_base/urdf/hunter_se.urdf.xacro`

### 文档
- `docs/ROS_TOPICS_API.md` - ROS话题接口
- `docs/ROS_TOPICS_QUICK_REF.md` - 快速参考
- `docs/代码阅读指引.md` - 代码阅读指引
- `docs/新人入门指南.md` - 入门指南
- `docs/GIT_WORKFLOW.md` - Git Flow指南
- `Localization/rob_localization/docs/robot_localization_guide.md` - EKF配置指南
- `Localization/rob_localization/docs/troubleshooting_ekf_nan.md` - EKF问题排查

### 配置参考

**Revo Bridge** (`config/revo_bridge_config.json`)：
- `pose_publish_rate_hz` - 发布频率
- `cmd_vel_in_physical_units: true` - 标准ROS Twist单位
- `linear_scale` / `angular_scale` - 最大安全速度

**里程计** (revo_odom_node.py)：
- `odom_smoothing_alpha`: 0.0-1.0，越小越平滑
- `odom_deadzone_linear`: 防止静止漂移
- `gnss_good_window`: GPS采样窗口

**GPS导航** (planning/gps_nav2/config/)：
- GPS航点容差、Nav2行为树、室外导航参数
