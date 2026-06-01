# ROS 话题快速参考卡片 / Quick Reference Card

> 前端开发者常驻文档 - 快速查找所需话题和数据格式

---

## 🚗 机器人状态订阅 (State Subscription)

### 位姿 & 位置

```bash
Topic: /revo/pose
Type: revo_msgs/msg/PoseState
Rate: 10 Hz
```

```javascript
// 数据转换公式
const pose = {
  lon: msg.longitude / 1e7,      // °
  lat: msg.latitude / 1e7,       // °
  alt: msg.altitude / 10,        // m
  roll: msg.roll / 1000,         // rad
  pitch: msg.pitch / 1000,       // rad
  yaw: msg.yaw / 1000,           // rad (需取反)
  vx: msg.wheel_linear_velocity / 100,    // m/s
  wz: msg.wheel_angular_velocity / 1000   // rad/s (需取反)
};
```

### 里程计

```bash
Topic: /odom
Type: nav_msgs/msg/Odometry
Rate: 10 Hz
```

```javascript
const odom = {
  x: msg.pose.pose.position.x,        // m
  y: msg.pose.pose.position.y,        // m
  yaw: quaternionToYaw(msg.pose.pose.orientation), // rad
  vx: msg.twist.twist.linear.x,       // m/s
  wz: msg.twist.twist.angular.z       // rad/s
};
```

### 电池状态

```bash
Topic: /revo/battery
Type: revo_msgs/msg/BatteryStatus
Rate: 1 Hz
```

```javascript
const battery = {
  count: msg.battery_count,
  percent: msg.remaining_capacity,    // 0-100
  power: msg.power                    // W
};
```

### 系统状态

```bash
Topic: /revo/system_status
Type: revo_msgs/msg/SystemStatus
Rate: 1 Hz
```

```javascript
// 控制模式
const MODES = {
  1: 'LOCKED',
  2: 'REMOTE',
  3: 'CRUISE',
  4: 'ROUTE',
  5: 'FOLLOW',
  6: 'SDK'
};
const mode = MODES[msg.control_mode] || 'UNKNOWN';
```

---

## 🎮 控制命令发布 (Command Publishing)

### 速度控制

```bash
Topic: /revo/cmd_vel
Type: geometry_msgs/msg/Twist
```

```javascript
// 前进 0.5 m/s
function forward(speed = 0.5) {
  publish('/revo/cmd_vel', {
    linear: { x: speed, y: 0, z: 0 },
    angular: { x: 0, y: 0, z: 0 }
  });
}

// 原地旋转 (rad/s, 正值右转, 负值左转)
function rotate(omega = 0.5) {
  publish('/revo/cmd_vel', {
    linear: { x: 0, y: 0, z: 0 },
    angular: { x: 0, y: 0, z: -omega }
  });
}

// 停止
function stop() {
  publish('/revo/cmd_vel', {
    linear: { x: 0, y: 0, z: 0 },
    angular: { x: 0, y: 0, z: 0 }
  });
}
```

---

## 📷 传感器数据 (Sensors)

### 摄像头

```bash
Topic: /image_raw
Type: sensor_msgs/msg/Image
Rate: 30 Hz
```

```javascript
// 图像数据是 Base64 编码的字节数组
// 需要解码后显示
const imageData = atob(msg.data);
const blob = new Blob([imageData], { type: 'image/jpeg' });
const url = URL.createObjectURL(blob);
imgElement.src = url;
```

### 激光雷达

```bash
Topic: /scan
Type: sensor_msgs/msg/LaserScan
Rate: 10 Hz
```

```javascript
// ranges 数组包含 360 个距离值
const scan = {
  angleMin: msg.angle_min,    // rad
  angleMax: msg.angle_max,    // rad
  ranges: msg.ranges,         // float[], 单位: m
  rangeMin: msg.range_min,    // m
  rangeMax: msg.range_max     // m
};
```

### YOLO 障碍物

```bash
Topic: /yolo_obstacles
Type: yolo_msgs/msg/YoloObstacleArray
```

```javascript
msg.obstacles.forEach(obj => {
  console.log({
    class: obj.label,         // 'person', 'car', ...
    confidence: obj.score,    // 0-1
    distance: obj.distance,   // m
    position: { x: obj.x, y: obj.y, z: obj.z }  // 相机坐标系, m
  });
});
```

---

## 🔌 WebSocket 连接 (Foxglove)

```javascript
// 连接
const ws = new WebSocket('ws://192.168.234.1:8765');

// 订阅
ws.send(JSON.stringify({
  op: 'subscribe',
  topic: '/revo/pose'
}));

// 接收
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.op === 'publish') {
    console.log(msg.msg);  // 话题数据
  }
};
```

---

## 📐 常用转换 (Conversions)

```javascript
// 四元数转航向角
function quaternionToYaw(q) {
  return Math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                    1.0 - 2.0 * (q.y * q.y + q.z * q.z));
}

// 弧度转度数
function radToDeg(rad) {
  return rad * 180 / Math.PI;
}

// 经纬度转米 (ENU 坐标, 近似)
function lonLatToMeters(lon, lat, lon0, lat0) {
  const R = 6378137;  // 地球半径
  const lat0Rad = lat0 * Math.PI / 180;
  const dx = (lon - lon0) * Math.PI / 180 * R * Math.cos(lat0Rad);
  const dy = (lat - lat0) * Math.PI / 180 * R;
  return { x: dx, y: dy };
}
```

---

## 🎨 UI 显示建议

### 仪表盘布局

```
┌─────────────────────────────────────────────┐
│  [摄像头画面]    [地图/轨迹]                 │
│  640x480         (odom位姿叠加)             │
├──────────────┬──────────────────────────────┤
│ 状态面板      │ 控制面板                    │
│ ├ 模式: SDK   │ ┌────┐ ┌────┐              │
│ ├ 电量: 85%   │ │ ↑  │ │    │ 前进          │
│ ├ 速度: 0.5   │ ├────┤ ├────┤              │
│ ├ 航向: 90°   │ │ ←  │ │ →  │              │
│ └ GPS: OK    │ └────┘ └────┘              │
│               │       ↓                     │
└──────────────┴──────────────────────────────┘
```

### 数据刷新频率

| 数据类型 | 建议频率 |
|----------|----------|
| 位姿/速度 | 10 Hz |
| 电池/状态 | 1 Hz (变化时更新) |
| 摄像头 | 15 Hz (降频) |
| 雷达点云 | 5 Hz (可选) |

---

## 🚨 错误处理

```javascript
// 检查数据有效性
function isPoseValid(msg) {
  return msg.longitude !== 0 && msg.latitude !== 0;
}

function isBatteryLow(msg) {
  return msg.remaining_capacity < 20;
}

function isMoving(msg) {
  return Math.abs(msg.wheel_linear_velocity) > 100; // >1m/s
}
```

---

**提示**: 完整文档见 [ROS_TOPICS_API.md](./ROS_TOPICS_API.md)
