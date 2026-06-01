# gps_goal_tool

GPS目标点工具 — 输入GPS坐标，自动转换为本地坐标，在rviz2中显示为目标点，并可选发送给Nav2导航。

## 功能

- GPS坐标(WGS84) → 本地坐标系(UTM相对坐标，单位米)转换
- 第一次收到有效GPS自动设为坐标原点 (0, 0)
- rviz2中显示红色箭头Marker + GPS坐标文本标签
- 可选自动发送 `PoseStamped` 目标给Nav2

## 坐标转换原理

```
WGS84 (经纬度)  ──pyproj──>  UTM (米)
                              │
                    减去原点UTM坐标
                              │
                              v
                         本地坐标 (米)
                        原点 = 机器人启动位置
```

1. 使用 pyproj 将 WGS84 (EPSG:4326) 投影到 UTM (如 EPSG:32651)
2. 记录机器人启动时的UTM坐标作为原点
3. 所有GPS坐标转换为相对于原点的偏移量(米)

## 依赖安装

```bash
# Python依赖
pip3 install pyproj

# ROS2依赖（通常已安装）
sudo apt install ros-humble-robot-localization ros-humble-nav2-bringup
```

## 编译

```bash
cd /home/orin/Workspace/agri_ugv/ros2_ws
colcon build --packages-select gps_goal_tool
source install/setup.bash
```

## 快速使用

### 方式一：测试模式（无需机器人、无需Nav2）

仅测试GPS坐标转换和rviz2显示：

```bash
# 1. 启动GPS目标点工具（手动设置原点，自动发布map->odom TF）
cd /home/orin/Workspace/agri_ugv/ros2_ws && source install/setup.bash && ros2 launch gps_goal_tool gps_goal_tool.launch.py \
  origin_mode:=manual \
  origin_latitude:=30.2552028 \
  origin_longitude:=120.2941317 \
  publish_static_tf:=true

# 2. 发送GPS目标点
cd /home/orin/Workspace/agri_ugv/ros2_ws && source install/setup.bash && ros2 topic pub --once /gps_goal_input sensor_msgs/msg/NavSatFix \
  "{latitude: 30.255386, longitude: 120.2940392, altitude: 0.0}"

# 3. 打开rviz2查看
rviz2
# 在rviz2中添加:
#   - TF display (查看map->odom->base_footprint)
#   - MarkerArray display (话题: /gps_goal_marker)
```

### 方式二：完整导航（机器人 + Nav2）

#### 1. 启动机器人底盘
```bash
ros2 launch revo_ugv_ros2 revo_bringup.launch.py
```

#### 2. 启动Nav2
```bash
source /opt/ros/humble/setup.bash
ros2 launch nav2_bringup navigation_launch.py \
  params_file:=/home/orin/Workspace/nav2_params_turtlebot4.yaml \
  map:=/home/orin/Workspace/agri_ugv/ros2_ws/maps/a2f4/a2f42map.yaml
```

#### 3. 启动GPS目标点工具
```bash
cd /home/orin/Workspace/agri_ugv/ros2_ws && source install/setup.bash && ros2 launch gps_goal_tool gps_goal_tool.launch.py
```

或单独运行节点：

```bash
cd /home/orin/Workspace/agri_ugv/ros2_ws && source install/setup.bash && ros2 run gps_goal_tool gps_goal_marker
```

### 4. 发送GPS目标点

```bash
cd /home/orin/Workspace/agri_ugv/ros2_ws && source install/setup.bash && ros2 topic pub --once /gps_goal_input sensor_msgs/msg/NavSatFix \
  "{latitude: 30.255386, longitude: 120.2940392, altitude: 0.0}"
```

### 5. rviz2中查看

在rviz2中添加 **MarkerArray** display，话题选择 `/gps_goal_marker`，即可看到红色箭头和坐标标签。

## ROS2 话题

| 话题 | 类型 | 方向 | 说明 |
|------|------|------|------|
| `/gps/fix` | `sensor_msgs/NavSatFix` | 订阅 | 机器人GPS，用于初始化原点 |
| `/gps_goal_input` | `sensor_msgs/NavSatFix` | 订阅 | 输入GPS目标点 |
| `/gps_goal_marker` | `visualization_msgs/Marker` | 发布 | rviz2可视化Marker |
| `/goal_pose` | `geometry_msgs/PoseStamped` | 发布 | Nav2导航目标 |

### 查看发布的坐标

发送GPS目标点后，可以查看转换后的本地坐标：

```bash
# 查看rviz2 Marker（包含本地坐标）
ros2 topic echo /gps_goal_marker

# 查看Nav2目标（PoseStamped格式）
ros2 topic echo /goal_pose
```

示例输出：
```yaml
# /gps_goal_marker
header:
  frame_id: map
pose:
  position:
    x: 123.45      # 本地x坐标(米)
    y: 67.89       # 本地y坐标(米)
    z: 0.0

# /goal_pose
header:
  frame_id: map
pose:
  position:
    x: 123.45
    y: 67.89
```

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `utm_zone` | `"51N"` | UTM分区号，中国东部51N，西部48N |
| `map_frame` | `"map"` | map坐标系名称 |
| `marker_scale` | `1.0` | Marker可视化缩放 |
| `auto_send_nav2_goal` | `true` | 是否自动发送Nav2目标 |
| `origin_mode` | `"auto"` | 原点模式: `auto` 从GPS话题获取, `manual` 手动指定 |
| `origin_latitude` | `0.0` | 手动原点纬度（仅manual模式） |
| `origin_longitude` | `0.0` | 手动原点经度（仅manual模式） |
| `manual_yaw_deg` | `"auto"` | 手动指定航向角(度)，"auto"表示自动从odom获取 |
| `publish_static_tf` | `"true"` | 是否发布静态 map->odom TF（测试用） |

### 坐标系转换说明

本工具正确处理了GPS坐标系和机器人坐标系之间的转换：

**UTM坐标系** (GPS转换后):
- x轴：东向
- y轴：北向

**ROS机器人坐标系** (REP-103标准):
- x轴：前进方向
- y轴：左侧
- yaw：绕z轴，**逆时针为正**（左转为正）

**自动朝向获取** (默认):
节点会订阅 `/odom` 话题，在GPS原点初始化时自动记录机器人的朝向角，无需手动设置。

**手动指定航向角** (可选):
如果需要手动指定，使用 `manual_yaw_deg` 参数，角度定义：
- 0° = 正北
- 90° = 正东
- 180° = 正南
- 270° = 正西

示例：
```bash
ros2 launch gps_goal_tool gps_goal_tool.launch.py \
  manual_yaw_deg:=90.0  # 机器人朝向正东
```

### 调试模式（手动设置原点）

不需要机器人GPS，直接指定原点坐标：

```bash
ros2 launch gps_goal_tool gps_goal_tool.launch.py \
  origin_mode:=manual \
  origin_latitude:=30.2552028 \
  origin_longitude:=120.2941317 \
  publish_static_tf:=true
```

航向角会自动从 `/odom` 获取。如需手动指定，添加 `manual_yaw_deg:=90`（正东）。

或单独运行节点：

```bash
ros2 run gps_goal_tool gps_goal_marker --ros-args \
  -p origin_mode:=manual \
  -p origin_latitude:=30.2552028 \
  -p origin_longitude:=120.2941317
```

### 启动时覆盖参数

```bash
ros2 launch gps_goal_tool gps_goal_tool.launch.py \
  utm_zone:=48N \
  marker_scale:=2.0 \
  auto_send_nav2_goal:=false
```

## 文件结构

```
gps_goal_tool/
├── config/
│   └── params.yaml                # 参数配置
├── launch/
│   └── gps_goal_tool.launch.py    # 启动文件
├── gps_goal_tool/
│   ├── coordinate_converter.py    # 坐标转换核心（纯Python，无ROS依赖）
│   ├── gps_goal_marker.py         # ROS2主节点
│   └── static_map_odom_tf.py      # 静态TF发布器（测试用，map->odom）
├── package.xml
└── setup.py
```

## coordinate_converter 模块

坐标转换核心类，不依赖ROS，可独立使用：

```python
from gps_goal_tool.coordinate_converter import CoordinateConverter

converter = CoordinateConverter(utm_zone='51N')

# 设置原点（机器人当前位置）
converter.set_origin(lat=30.2550, lon=120.2940)

# GPS → 本地坐标
x, y = converter.gps_to_local(lat=30.2560, lon=120.2950)
print(f"({x:.2f}, {y:.2f}) 米")  # 相对原点的偏移

# 本地坐标 → GPS
lat, lon = converter.local_to_gps(x=100.0, y=50.0)
```

## TF坐标系说明

### 完整导航TF树

```
map -> odom -> base_footprint -> base_link -> sensors
```

- **map**: 全局坐标系（GPS坐标转换后的地图坐标）
- **odom**: 里程计坐标系（机器人里程计原点）
- **base_footprint**: 机器人底盘
- **base_link**: 机器人中心

### map->odom TF 来源

| 场景 | map->odom 来源 | 说明 |
|------|----------------|------|
| 室内SLAM | AMCL | 使用粒子滤波定位 |
| 室外GPS | robot_localization (EKF) | 融合GPS+里程计 |
| **纯测试** | **static_map_odom_tf** | **静态零偏移，仅测试用** |

本包提供的 `static_map_odom_tf` 节点会发布一个零偏移的静态TF，将map和odom设为同一位置，用于：
- 纯GPS坐标转换测试
- 不需要实际导航的场景
- rviz2中查看GPS目标点

### 启用静态TF

```bash
# launch方式 (默认启用)
ros2 launch gps_goal_tool gps_goal_tool.launch.py publish_static_tf:=true

# 或单独运行
ros2 run gps_goal_tool static_map_odom_tf
```

## 常见UTM分区

| 地区 | UTM Zone |
|------|----------|
| 中国东部（浙江、上海） | 51N |
| 中国中部（四川、重庆） | 48N |
| 中国西部（新疆） | 45N |
| 日本 | 54N |
