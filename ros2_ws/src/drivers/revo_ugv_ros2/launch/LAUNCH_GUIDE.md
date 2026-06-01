# Revo UGV Launch 文件使用说明

## 新的 Launch 文件结构

为了方便调试和开发，我们将原来的 `revo_bringup.launch.py` 拆分为三个独立的launch文件：

### 1. revo_chassis.launch.py - 底盘节点
**用途**: 仅启动 Revo SDK 桥接节点和机器人模型

**启动内容**:
- Revo SDK 桥接节点 (`revo_bridge`)
- 机器人状态发布器 (`robot_state_publisher`)
- 关节状态发布器 (`joint_state_publisher`)
- 静态 TF 发布 (camera, lidar, laser)

**使用场景**: 当底盘连接不稳定需要频繁重启时

**启动命令**:
```bash
ros2 launch revo_ugv_ros2 revo_chassis.launch.py
```

**可选参数**:
- `host:=192.168.234.1` - Revo 底盘 IP 地址
- `client_name:=RevoUGV` - 客户端名称
- `use_sim_time:=false` - 使用仿真时间

---

### 2. revo_sensors.launch.py - 传感器节点
**用途**: 启动除底盘外的所有传感器和处理节点

**启动内容**:
- 里程计节点 (`revo_odom`)
- GNSS 节点 (`revo_gnss`)
- 摄像头节点 (`v4l2_camera`)
- 激光雷达节点 (`rplidar_ros`)
- Foxglove 调试桥

**使用场景**: 当需要重启传感器节点时

**启动命令**:
```bash
ros2 launch revo_ugv_ros2 revo_sensors.launch.py
```

**可选参数**:
- `camera_device:=/dev/video0` - 摄像头设备路径
- `camera_frame_rate:=30.0` - 摄像头帧率
- `lidar_port:=/dev/ttyUSB0` - 激光雷达串口
- `odom_publish_rate_hz:=10` - 里程计发布频率
- `odom_smoothing_alpha:=0.5` - 里程计平滑系数
- `foxglove_port:=8765` - Foxglove 端口

---

### 3. revo_all.launch.py - 完整启动
**用途**: 一次性启动底盘和所有传感器节点

**使用场景**: 正常运行时使用

**启动命令**:
```bash
ros2 launch revo_ugv_ros2 revo_all.launch.py
```

**可选参数**: 包含所有上述参数

---

## 使用示例

### 场景 1: 首次启动（推荐）

```bash
# 终端 1: 启动底盘
ros2 launch revo_ugv_ros2 revo_chassis.launch.py

# 终端 2: 启动传感器
ros2 launch revo_ugv_ros2 revo_sensors.launch.py
```

### 场景 2: 快速启动（一次性）

```bash
# 启动所有节点
ros2 launch revo_ugv_ros2 revo_all.launch.py
```

### 场景 3: 底盘断线重连

```bash
# 只需重启底盘节点，传感器保持运行
ros2 launch revo_ugv_ros2 revo_chassis.launch.py
```

### 场景 4: 更换激光雷达端口

```bash
# 终端 1: 启动底盘
ros2 launch revo_ugv_ros2 revo_chassis.launch.py

# 终端 2: 指定激光雷达端口启动传感器
ros2 launch revo_ugv_ros2 revo_sensors.launch.py lidar_port:=/dev/ttyUSB1
```

---

## 兼容性说明

原有的 `revo_bringup.launch.py` 仍然可用，功能与 `revo_all.launch.py` 相同：

```bash
# 旧的启动方式（仍然有效）
ros2 launch revo_ugv_ros2 revo_bringup.launch.py
```

---

## 故障排查

### 问题 1: 底盘连接失败

```bash
# 检查网络连接
ping 192.168.234.1

# 重启底盘节点
ros2 launch revo_ugv_ros2 revo_chassis.launch.py
```

### 问题 2: 激光雷达无数据

```bash
# 检查串口设备
ls -l /dev/ttyUSB*

# 重启传感器节点（指定正确端口）
ros2 launch revo_ugv_ros2 revo_sensors.launch.py lidar_port:=/dev/ttyUSB0
```

### 问题 3: 摄像头无图像

```bash
# 检查摄像头设备
ls -l /dev/video*

# 重启传感器节点（指定正确设备）
ros2 launch revo_ugv_ros2 revo_sensors.launch.py camera_device:=/dev/video1
```

---

## 节点关系图

```
revo_chassis.launch.py          revo_sensors.launch.py
┌─────────────────────┐         ┌──────────────────────┐
│                     │         │                      │
│  revo_bridge        │────────>│  revo_odom           │
│  (底盘桥接)          │ 底盘数据 │  (里程计)            │
│                     │         │                      │
│  robot_state_pub    │         │  revo_gnss           │
│  joint_state_pub    │         │  (GNSS)              │
│  static TF          │         │                      │
│                     │         │  v4l2_camera         │
└─────────────────────┘         │  (摄像头)             │
         │                      │                      │
         │ TF                   │  rplidar_node        │
         │                      │  (激光雷达)           │
         ▼                      │                      │
   ┌──────────┐                 │  foxglove_bridge     │
   │ TF Tree  │                 │  (调试桥)             │
   └──────────┘                 └──────────────────────┘
```

---

## 文件位置

所有 launch 文件位于:
```
ros2_ws/src/drivers/revo_ugv_ros2/launch/
├── revo_chassis.launch.py      # 底盘节点
├── revo_sensors.launch.py      # 传感器节点
├── revo_all.launch.py          # 完整启动
└── revo_bringup.launch.py      # 原始启动文件（兼容）
```
