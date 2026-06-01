# ROS2 话题接口文档 / ROS2 Topics API Documentation

本文档描述农业UGV项目中的ROS2话题及其消息格式，用于前端数据对接。
This document describes ROS2 topics and message formats for the agricultural UGV project for frontend integration.

---

## 目录 / Table of Contents

1. [XAG Revo 机器人话题](#xag-revo-机器人话题)
2. [Hunter SE 机器人话题](#hunter-se-机器人话题)
3. [通用话题](#通用话题)
4. [传感器话题](#传感器话题)
5. [YOLO 目标检测](#yolo-目标检测)
6. [数据单位转换说明](#数据单位转换说明)
7. [WebSocket 接入方式](#websocket-接入方式)

---

## XAG Revo 机器人话题

### 1. 位姿数据 `/revo/pose`

**话题类型**: `revo_msgs/msg/PoseState`

**发布频率**: 10 Hz (可配置)

**用途**: 机器人底盘位姿、GNSS、IMU、轮速数据

**消息格式**:
```json
{
  "header": {
    "stamp": {
      "sec": 1234567890,        // 秒部分
      "nanosec": 123456789      // 纳秒部分
    },
    "frame_id": "base_link"     // 坐标系ID
  },
  "longitude": 1131234567,      // 经度 (原始值, 实际° = 值/1e7)
  "latitude": 231234567,        // 纬度 (原始值, 实际° = 值/1e7)
  "altitude": 1234,             // 高度 (原始值, 实际m = 值/10)
  "roll": 15,                   // 横滚角 (原始值, 实际rad = 值/1000)
  "pitch": -5,                  // 俯仰角 (原始值, 实际rad = 值/1000)
  "yaw": 1570,                  // 航向角 (原始值, 实际rad = 值/1000)
  "fused_linear_velocity": 50,  // 融合线速度 (原始值, 实际m/s = 值/100)
  "fused_angular_velocity": 300,// 融合角速度 (原始值, 实际rad/s = 值/1000)
  "wheel_linear_velocity": 48,  // 轮速计线速度 (原始值, 实际m/s = 值/100)
  "wheel_angular_velocity": 295 // 轮速计角速度 (原始值, 实际rad/s = 值/1000)
}
```

**转换后示例 (实际物理值)**:
```json
{
  "longitude_deg": 113.1234567,
  "latitude_deg": 23.1234567,
  "altitude_m": 123.4,
  "roll_rad": 0.015,
  "pitch_rad": -0.005,
  "yaw_rad": 1.57,
  "fused_linear_velocity_ms": 0.5,
  "fused_angular_velocity_rads": 0.3,
  "wheel_linear_velocity_ms": 0.48,
  "wheel_angular_velocity_rads": 0.295
}
```

---

### 2. 系统状态 `/revo/system_status`

**话题类型**: `revo_msgs/msg/SystemStatus`

**发布频率**: 1 Hz (可配置)

**用途**: 机器人控制模式、定位状态、电池状态、电机状态

**消息格式**:
```json
{
  "header": {
    "stamp": {"sec": 1234567890, "nanosec": 123456789},
    "frame_id": "base_link"
  },
  "control_mode": 6,           // 控制模式 (见下文说明)
  "reserved": [0, 0, 0],       // 保留位
  "positioning_status": 0,     // 定位系统状态 (位掩码)
  "battery_status": 0,         // 电池系统状态 (位掩码)
  "chassis_status": 0,         // 底盘状态 (位掩码)
  "motor_status": [            // 8个电机状态数组
    0, 0, 0, 0, 0, 0, 0, 0
  ]
}
```

**控制模式 (control_mode)**:
| 值 | 模式 | 说明 |
|----|------|------|
| 1  | 上锁 | Locked |
| 2  | 遥控 | Remote Control |
| 3  | 定速 | Constant Speed |
| 4  | 航线 | Route Following |
| 5  | 跟行 | Line Following |
| 6  | SDK | SDK Control (PC控制) |

---

### 3. 电池状态 `/revo/battery`

**话题类型**: `revo_msgs/msg/BatteryStatus`

**发布频率**: 1 Hz (可配置)

**消息格式**:
```json
{
  "header": {
    "stamp": {"sec": 1234567890, "nanosec": 123456789},
    "frame_id": "base_link"
  },
  "battery_count": 2,          // 电池数量
  "remaining_capacity": 85,    // 剩余电量百分比 (0-100)
  "power": 450                 // 系统功率 (W)
}
```

---

### 4. 里程计 `/odom`

**话题类型**: `nav_msgs/msg/Odometry`

**发布频率**: 10 Hz

**用途**: 机器人里程计数据，包含位置、姿态和速度

**消息格式**:
```json
{
  "header": {
    "stamp": {"sec": 1234567890, "nanosec": 123456789},
    "frame_id": "odom"
  },
  "child_frame_id": "base_footprint",
  "pose": {
    "pose": {
      "position": {
        "x": 1.23,             // X位置 (m)
        "y": 4.56,             // Y位置 (m)
        "z": 0.0               // Z位置 (m, 通常为0)
      },
      "orientation": {
        "x": 0.0,
        "y": 0.0,
        "z": 0.707,            // 四元数Z分量
        "w": 0.707             // 四元数W分量
      }
    },
    "covariance": [            // 位置协方差矩阵 (6x6)
      0.0001, 0.0, 0.0, 0.0, 0.0, 0.0,
      0.0, 0.0001, 0.0, 0.0, 0.0, 0.0,
      ...
    ]
  },
  "twist": {
    "twist": {
      "linear": {
        "x": 0.5,              // 线速度 (m/s)
        "y": 0.0,
        "z": 0.0
      },
      "angular": {
        "x": 0.0,
        "y": 0.0,
        "z": 0.3               // 角速度 (rad/s)
      }
    },
    "covariance": [...]         // 速度协方差矩阵
  }
}
```

**注意事项**:
- Revo 里程计使用 `base_footprint` 作为子坐标系
- 位置信息基于轮速计积分，累积误差随时间增加
- 姿态角度来自 IMU，更准确

---

### 5. 速度命令 `/revo/cmd_vel`

**话题类型**: `geometry_msgs/msg/Twist`

**用途**: 发送速度控制命令到 Revo 机器人

**消息格式**:
```json
{
  "linear": {
    "x": 0.5,                  // 前进速度 (m/s), 正值前进, 负值后退
    "y": 0.0,                  // 侧向速度 (通常为0)
    "z": 0.0
  },
  "angular": {
    "x": 0.0,
    "y": 0.0,
    "z": -0.3                  // 旋转速度 (rad/s), 正值右转, 负值左转
  }
}
```

**速度限制** (可通过配置文件调整):
- 线速度: 最大 ±2.0 m/s
- 角速度: 最大 ±2.0 rad/s

---

## Hunter SE 机器人话题

### 1. Hunter 状态 `/ugv_status`

**话题类型**: `hunter_msgs/msg/HunterStatus`

**发布频率**: 50 Hz

**消息格式**:
```json
{
  "header": {
    "stamp": {"sec": 1234567890, "nanosec": 123456789},
    "frame_id": "base_link"
  },
  "linear_velocity": 0.5,      // 当前线速度 (m/s)
  "steering_angle": 0.1,       // 转向角 (rad)
  "vehicle_state": 2,          // 车辆状态
  "control_mode": 1,           // 控制模式
  "error_code": 0,             // 错误代码
  "battery_voltage": 48.2,     // 电池电压 (V)
  "actuator_states": [         // 执行器状态
    {
      "motor_id": 0,           // 电机ID (0:前右, 1:前左, 2:后右, 3:后左)
      "current": 1.2,          // 电流 (A)
      "rpm": 150,              // 转速 (RPM)
      "temperature": 45        // 温度 (°C)
    },
    ...
  ]
}
```

---

### 2. 速度命令 `/cmd_vel`

**话题类型**: `geometry_msgs/msg/Twist`

**用途**: 发送速度控制命令到 Hunter 机器人

**消息格式** (与 Revo 相同):
```json
{
  "linear": {
    "x": 0.5,                  // 前进速度 (m/s)
    "y": 0.0,
    "z": 0.0
  },
  "angular": {
    "x": 0.0,
    "y": 0.0,
    "z": 0.3                   // 旋转速度 (rad/s)
  }
}
```

---

## 通用话题

### 1. TF 变换 `/tf`

**话题类型**: `tf2_msgs/msg/TFMessage`

**用途**: 坐标系变换关系

**Revo 坐标系树**:
```
odom
 └─ base_footprint
     └─ base_link
         ├─ camera (0.4, 0.2, 0.16)
         └─ lidar (0.4, 0, 0.2)
             └─ laser
```

**Hunter 坐标系树**:
```
odom
 └─ base_link
```

---

## 传感器话题

### 1. 摄像头图像 `/image_raw`

**话题类型**: `sensor_msgs/msg/Image`

**发布频率**: 30 Hz

**消息格式**:
```json
{
  "header": {
    "stamp": {"sec": 1234567890, "nanosec": 123456789},
    "frame_id": "camera"
  },
  "height": 480,               // 图像高度
  "width": 640,                // 图像宽度
  "encoding": "bgr8",          // 编码格式
  "is_bigendian": 0,           // 字节序
  "step": 1920,                // 每行字节数
  "data": "<base64>"           // 图像数据 (二进制, Base64编码用于传输)
}
```

**摄像头参数** (可配置):
- 设备: `/dev/video0`
- 分辨率: 640x480 (可设为 1280x720 或 1920x1080)
- 帧率: 30 Hz

---

### 2. 激光雷达 `/scan`

**话题类型**: `sensor_msgs/msg/LaserScan`

**发布频率**: 10 Hz

**消息格式**:
```json
{
  "header": {
    "stamp": {"sec": 1234567890, "nanosec": 123456789},
    "frame_id": "laser"
  },
  "angle_min": -3.14159,       // 最小扫描角度 (rad)
  "angle_max": 3.14159,        // 最大扫描角度 (rad)
  "angle_increment": 0.01745,  // 角度增量 (rad)
  "time_increment": 0.000,     // 时间增量
  "scan_time": 0.1,            // 扫描时间 (s)
  "range_min": 0.15,           // 最小距离 (m)
  "range_max": 12.0,           // 最大距离 (m)
  "ranges": [                  // 距离数组 (m)
    1.2, 1.5, 1.8, ...
  ],
  "intensities": [...]         // 强度数组 (可选)
}
```

---

### 3. GPS 数据 `/gps/fix`

**话题类型**: `sensor_msgs/msg/NavSatFix`

**发布频率**: 1 Hz

**消息格式**:
```json
{
  "header": {
    "stamp": {"sec": 1234567890, "nanosec": 123456789},
    "frame_id": "gps"
  },
  "status": {
    "status": 0,               // 状态 (-1:无数据, 0:未增强, 1:SBAS, 2:GBAS)
    "service": 1               // 服务 (1:GPS, 2:GLONASS, 4:Galileo, 8:BeiDou)
  },
  "latitude": 23.1234567,      // 纬度 (deg)
  "longitude": 113.1234567,    // 经度 (deg)
  "altitude": 123.4,           // 高度 (m)
  "covariance": [...]          // 协方差矩阵
}
```

---

## YOLO 目标检测

### 1. 障碍物检测 `/yolo_obstacles`

**话题类型**: `yolo_msgs/msg/YoloObstacleArray`

**发布频率**: 10-30 Hz

**消息格式**:
```json
{
  "header": {
    "stamp": {"sec": 1234567890, "nanosec": 123456789},
    "frame_id": "camera"
  },
  "obstacles": [
    {
      "label": "person",       // 目标类别
      "score": 0.92,           // 置信度 (0-1)
      "distance": 5.2,         // 距离 (m)
      "x": 0.5,                // X坐标 (相机坐标系, m)
      "y": 0.0,                // Y坐标 (相机坐标系, m)
      "z": 1.6                 // Z坐标 (相机坐标系, m)
    },
    {
      "label": "car",
      "score": 0.87,
      "distance": 12.3,
      "x": 2.1,
      "y": 0.5,
      "z": 1.5
    }
  ],
  "count": 2                   // 障碍物总数
}
```

**常见目标类别** (取决于 YOLO 模型训练):
- `person` - 人
- `car` - 汽车
- `truck` - 卡车
- `bicycle` - 自行车
- `dog` - 狗
- 等等...

---

## 数据单位转换说明

### Revo 话题数据转换

Revo SDK 使用缩放后的整数传输数据，需要转换：

| 字段 | 存储格式 | 转换公式 | 示例 |
|------|----------|----------|------|
| 经度 | int32 | `longitude / 1e7` | `1131234567 → 113.1234567°` |
| 纬度 | int32 | `latitude / 1e7` | `231234567 → 23.1234567°` |
| 高度 | int16 | `altitude / 10.0` | `1234 → 123.4m` |
| 姿态角 | int16 | `angle / 1000.0` | `1570 → 1.57rad` |
| 线速度 | int16 | `velocity / 100.0` | `50 → 0.5m/s` |
| 角速度 | int16 | `omega / 1000.0` | `300 → 0.3rad/s` |

**坐标系转换**:
Revo 使用右手系 (顺时针为正)，ROS 使用左手系 (逆时针为正):
- Yaw 角需要取反: `ros_yaw = -revo_yaw`

---

## WebSocket 接入方式

### 使用 Foxglove Bridge

项目已集成 Foxglove Bridge，可通过 WebSocket 直接订阅话题：

**连接地址**: `ws://<机器人IP>:8765`

**使用示例** (JavaScript):

```javascript
// 连接到 Foxglove Bridge
const ws = new WebSocket('ws://192.168.234.1:8765');

// 订阅位姿数据
ws.send(JSON.stringify({
  op: 'subscribe',
  topic: '/revo/pose'
}));

// 接收消息
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.op === 'publish') {
    const data = message.msg;

    // 转换数据
    const pose = {
      longitude: data.longitude / 1e7,
      latitude: data.latitude / 1e7,
      altitude: data.altitude / 10,
      yaw: data.yaw / 1000,
      linearVelocity: data.wheel_linear_velocity / 100,
      timestamp: data.header.stamp.sec * 1000 + Math.floor(data.header.stamp.nanosec / 1000000)
    };

    // 更新UI
    updatePoseDisplay(pose);
  }
};

// 发送速度命令
function sendVelocity(linear, angular) {
  const cmd = {
    op: 'publish',
    topic: '/revo/cmd_vel',
    msg: {
      linear: { x: linear, y: 0.0, z: 0.0 },
      angular: { x: 0.0, y: 0.0, z: -angular }
    }
  };
  ws.send(JSON.stringify(cmd));
}
```

---

### 使用 rosbridge_suite

如果需要更灵活的接口，可以安装 rosbridge_suite：

**安装**:
```bash
sudo apt install ros-humble-rosbridge-server
```

**启动**:
```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

**连接地址**: `ws://<机器人IP>:9090`

**API 示例**:

```javascript
// 订阅话题
ws.send(JSON.stringify({
  op: 'subscribe',
  type: 'revo_msgs/msg/PoseState',
  topic: '/revo/pose'
}));

// 发布话题
ws.send(JSON.stringify({
  op: 'publish',
  type: 'geometry_msgs/msg/Twist',
  topic: '/revo/cmd_vel',
  msg: {
    linear: { x: 0.5, y: 0.0, z: 0.0 },
    angular: { x: 0.0, y: 0.0, z: -0.3 }
  }
}));

// 调用服务
ws.send(JSON.stringify({
  op: 'call_service',
  service: '/reset_odom',
  args: {}
}));
```

---

## 前端集成建议

### 1. 数据更新频率

根据话题发布频率合理更新UI：

| 话题 | 频率 | UI 更新建议 |
|------|------|-------------|
| `/revo/pose` | 10 Hz | 每次更新 |
| `/odom` | 10 Hz | 每次更新 |
| `/image_raw` | 30 Hz | 考虑降频到 10-15 Hz |
| `/revo/battery` | 1 Hz | 每次更新 |
| `/revo/system_status` | 1 Hz | 仅当状态变化时提示 |

### 2. 机器人状态显示

建议显示的关键状态：

- **位置信息**: 经纬度、高度
- **姿态信息**: 航向角 (转换为度数显示)
- **速度信息**: 线速度、角速度
- **电池信息**: 剩余电量百分比、功率
- **控制模式**: 当前模式 (SDK/遥控/航线等)
- **系统状态**: 定位状态、底盘状态、电机状态

### 3. 控制命令发送

- 使用平滑的速度控制，避免突变
- 设置合理的速度限制
- 实现紧急停止功能
- 记录命令日志用于调试

---

## 常见问题

### Q1: 为什么经纬度是整数？
A: Revo SDK 使用定点数传输以节省带宽，需要除以 1e7 转换为度数。

### Q2: 为什么角速度需要取反？
A: Revo 使用右手坐标系 (顺时针为正)，ROS 标准是左手系 (逆时针为正)，需要转换。

### Q3: 如何判断 GPS 数据是否有效？
A: 检查 `positioning_status` 字段的位标志，或查看 GPS 话题的 status 值。

### Q4: Foxglove Bridge 连接失败？
A: 确保机器人已启动 (`ros2 launch revo_ugv_ros2 revo_bringup.launch.py`)，并检查防火墙设置。

---

## 附录：完整话题列表

运行以下命令获取实时话题列表：

```bash
# 查看所有话题
ros2 topic list

# 查看话题详细信息
ros2 topic info /revo/pose

# 查看话题消息类型定义
ros2 interface show revo_msgs/msg/PoseState

# 监听话题数据
ros2 topic echo /revo/pose
```

---

**文档版本**: 1.0
**最后更新**: 2026-03-22
**维护者**: agri_ugv 项目组
