# GPS目标点工具 - 快速使用指南

## 问题诊断

之前节点无法工作的原因：
1. ❌ GPS原点未初始化（需要 `/gps/fix` 或手动设置）
2. ❌ 机器人朝向未初始化（需要 `/odom/initial_yaw_offset`）

## 解决方案

### 方案1: 使用手动模式（推荐用于测试）

```bash
# 1. 启动节点（使用默认参数）
cd /home/orin/Workspace/agri_ugv/ros2_ws
source install/setup.bash
ros2 launch gps_goal_tool gps_goal_marker_manual.launch.py

# 2. 另一个终端发送GPS目标点
ros2 topic pub --once /gps_goal_input sensor_msgs/msg/NavSatFix \
  "{latitude: 30.2552028, longitude: 120.2941317, altitude: 0.0}"
```

### 方案2: 自定义参数启动

```bash
# 指定GPS原点和朝向角
ros2 launch gps_goal_tool gps_goal_marker_manual.launch.py \
  origin_latitude:=30.2552028 \
  origin_longitude:=120.2941317 \
  manual_yaw_deg:=0.0 \
  utm_zone:=51N
```

### 方案3: 使用配置文件

```bash
ros2 run gps_goal_tool gps_goal_marker --ros-args --params-file \
  src/planning/gps_goal_tool/config/manual_mode.yaml
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `origin_mode` | 原点模式: `auto`(从GPS获取) 或 `manual`(手动指定) | `auto` |
| `origin_latitude` | GPS原点纬度 | `30.2552028` |
| `origin_longitude` | GPS原点经度 | `120.2941317` |
| `use_manual_yaw` | 是否使用手动朝向角 | `false` |
| `manual_yaw_deg` | 机器人朝向角（度，正北为0） | `0.0` |
| `utm_zone` | UTM分区 | `51N` |

## 朝向角说明

`manual_yaw_deg` 参数：
- **0度** = 正北
- **90度** = 正东
- **180度** = 正南
- **270度** = 正西

**如何确定你的机器人朝向角**：
1. 在地图上找到机器人位置
2. 确定机器人前进方向相对于正北的角度
3. 顺时针方向为正

## RViz可视化

启动 RViz 后添加显示：
1. **Add** → **By topic** → **/gps_goal_marker** → **OK**

你应该看到：
- 🔴 红色箭头 - 目标点位置
- 📍 文本标签 - GPS坐标和本地坐标

## 完整测试流程

```bash
# 终端1: 启动节点
ros2 launch gps_goal_tool gps_goal_marker_manual.launch.py

# 终端2: 启动RViz
rviz2
# 在RViz中添加 /gps_goal_marker 显示

# 终端3: 发送多个目标点进行测试
# 测试点1: 正前方100米 (大约)
ros2 topic pub --once /gps_goal_input sensor_msgs/msg/NavSatFix \
  "{latitude: 30.2561028, longitude: 120.2941317, altitude: 0.0}"

# 测试点2: 右侧50米 (大约)
ros2 topic pub --once /gps_goal_input sensor_msgs/msg/NavSatFix \
  "{latitude: 30.2552028, longitude: 120.2946317, altitude: 0.0}"
```

## 验证节点状态

```bash
# 查看节点日志
ros2 node info /gps_goal_marker_node

# 查看话题列表
ros2 topic list | grep goal

# 监听Marker话题
ros2 topic echo /gps_goal_marker

# 监听Nav2目标话题
ros2 topic echo /goal_pose
```

## 故障排查

### 问题1: 没有Marker显示

**检查**:
```bash
ros2 topic echo /gps_goal_marker
```

**解决**:
- 确认节点已启动
- 检查 `origin_mode=manual`
- 检查GPS原点坐标是否正确

### 问题2: 没有发送Nav2目标

**检查**:
```bash
ros2 topic echo /goal_pose
```

**解决**:
- 确认 `auto_send_nav2_goal: true`
- 检查 Nav2 是否正在运行

### 问题3: 坐标转换错误

**检查日志输出**:
```
GPS目标点: (lat, lon)
  UTM: (x, y) [东,北]
  机器人: (x, y) [前,左]
  旋转角: XX°
```

**解决**:
- 检查 `utm_zone` 是否正确
- 检查 `manual_yaw_deg` 是否正确

## GPS坐标转换

**中国地区UTM分区**:
- 华东（上海、杭州）: 51N
- 华北（北京）: 50N
- 华南（广州）: 49N
- 华西（成都）: 48N

**在线GPS坐标查询**:
- 高德地图: https://ditu.amap.com/
- 谷歌地球: 显示经纬度坐标

## 自动模式（需要GPS设备）

如果你有真实的GPS设备，可以使用自动模式：

```bash
# 启动自动模式（需要/gps/fix和/odom/initial_yaw_offset话题）
ros2 run gps_goal_tool gps_goal_marker --ros-args \
  -p origin_mode:=auto \
  -p use_manual_yaw:=false
```

自动模式需要：
1. `/gps/fix` - GPS数据 (sensor_msgs/NavSatFix)
2. `/odom/initial_yaw_offset` - 初始朝向角 (geometry_msgs/Vector3)
