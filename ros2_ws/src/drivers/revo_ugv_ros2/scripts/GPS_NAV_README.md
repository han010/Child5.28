# GPS多点航点导航使用指南

## 功能概述

支持两种导航模式：
- **单点模式**：导航到单个GPS目标点
- **多点模式**：按顺序执行多个GPS航点，支持循环

## 快速开始

### 1. 启动Revo底盘
```bash
ros2 launch revo_ugv_ros2 revo_bringup.launch.py
```

### 2. 启动导航

#### 单点导航
```bash
ros2 run revo_ugv_ros2 gps_waypoint_nav_odom
```

#### 多点导航（使用launch文件）
```bash
ros2 launch revo_ugv_ros2 gps_waypoint_nav.launch.py \
  waypoint_list:='[{"latitude":30.2551044,"longitude":120.294113},{"latitude":30.2552000,"longitude":120.2942000}]'
```

## 参数配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `target_latitude` | 30.2551044 | 目标纬度（单点模式）|
| `target_longitude` | 120.294113 | 目标经度（单点模式）|
| `waypoint_list` | [] | 航点列表（JSON格式，多点模式）|
| `loop_waypoints` | false | 是否循环执行 |
| `tolerance` | 1.0 | 到达容差(米) |
| `linear_speed` | 0.5 | 前进速度(m/s) |
| `angular_speed` | 0.3 | 转向速度(rad/s) |
| `angle_tolerance` | 0.1 | 角度容差(rad) |
| `use_slow_approach` | true | 接近目标时减速 |
| `slow_distance` | 2.0 | 减速距离(米) |
| `slow_speed_ratio` | 0.3 | 减速比例 |
| `wait_at_waypoint` | 0.0 | 到达航点后等待时间(秒) |

## 使用示例

### 示例1：单点导航
```bash
ros2 run revo_ugv_ros2 gps_waypoint_nav_odom \
  --ros-args \
  -p target_latitude:=30.255500 \
  -p target_longitude:=120.294500 \
  -p tolerance:=0.5 \
  -p linear_speed:=0.3
```

### 示例2：矩形轨迹（农业巡检）
```bash
ros2 run revo_ugv_ros2 gps_waypoint_nav_odom \
  --ros-args \
  -p waypoint_list:='[{"latitude":30.2551044,"longitude":120.294113},{"latitude":30.2552000,"longitude":120.294113},{"latitude":30.2552000,"longitude":120.294250},{"latitude":30.2551044,"longitude":120.294250}]' \
  -p loop_waypoints:=true
```

### 示例3：使用配置文件
```bash
ros2 launch revo_ugv_ros2 gps_waypoint_nav.launch.py
```

## ROS2服务

| 服务 | 类型 | 说明 |
|------|------|------|
| `/start_mission` | Trigger | 开始/重新开始任务 |
| `/pause_mission` | Trigger | 暂停任务 |
| `/resume_mission` | Trigger | 恢复任务 |
| `/reset_mission` | Trigger | 重置到第一个航点 |
| `/set_loop_mode` | SetBool | 设置是否循环 |

### 调用示例
```bash
# 暂停任务
ros2 service call /pause_mission std_srvs/srv/Trigger

# 恢复任务
ros2 service call /resume_mission std_srvs/srv/Trigger

# 启用循环模式
ros2 service call /set_loop_mode std_srvs/srv/SetBool "{data: true}"
```

## ROS2话题

| 话题 | 类型 | 说明 |
|------|------|------|
| `/nav_status` | String | 导航状态信息（JSON格式） |

### 状态消息格式
```json
{
  "status": "active|paused|complete",
  "message": "状态描述",
  "current_waypoint": 2,
  "total_waypoints": 5,
  "position": {
    "x": 1.23,
    "y": 4.56,
    "yaw": 0.78
  }
}
```

### 监听状态
```bash
ros2 topic echo /nav_status
```

## 航点列表格式

### JSON格式
```json
[
  {"latitude": 30.2551044, "longitude": 120.294113},
  {"latitude": 30.2552000, "longitude": 120.2942000},
  {"latitude": 30.2553000, "longitude": 120.2943000}
]
```

### 获取GPS坐标
```bash
# 监听GPS话题获取当前坐标
ros2 topic echo /gps/fix
```

## 工作流程

```
1. GPS初始化
   └─> 记录当前位置为odom原点(0,0)

2. 航点转换
   └─> GPS坐标 -> odom坐标系(米)

3. 执行导航
   └─> 转向目标 -> 前进 -> 到达容差内

4. 下一个航点
   └─> 重复步骤3

5. 任务完成
   └─> 所有航点完成 或 循环重新开始
```

## 农业应用场景

### 1. 田块巡检
```bash
# 矩形轨迹绕田块一周
waypoint_list:=[
  {"lat":30.2551044,"lon":120.294113},  # 西南角
  {"lat":30.2552000,"lon":120.294113},  # 西北角
  {"lat":30.2552000,"lon":120.294250},  # 东北角
  {"lat":30.2551044,"lon":120.294250},  # 东南角
]
```

### 2. 之字形喷洒
```bash
# 来回穿梭
waypoint_list:=[
  {"lat":30.2551000,"lon":120.294100},
  {"lat":30.2551000,"lon":120.294200},
  {"lat":30.2551005,"lon":120.294200},
  {"lat":30.2551005,"lon":120.294100},
  {"lat":30.2551010,"lon":120.294100},
  {"lat":30.2551010,"lon":120.294200},
]
```

### 3. 多点采样
```bash
# 在多个采样点依次停靠
waypoint_list:=[
  {"lat":30.2551044,"lon":120.294113},
  {"lat":30.2551500,"lon":120.294150},
  {"lat":30.2551800,"lon":120.294180},
]
wait_at_waypoint:=5.0  # 每点等待5秒
```

## 故障排查

| 问题 | 可能原因 | 解决方法 |
|------|---------|---------|
| 无法初始化GPS | GPS信号弱 | 移至室外开阔处 |
| 偏离目标 | odom漂移 | 减小tolerance，定期重置 |
| 转向方向错误 | yaw未取反 | 检查代码中yaw取负 |
| 无法到达目标 | 容差太小 | 增大tolerance值 |
