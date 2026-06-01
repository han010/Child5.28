# Revo UGM 室内导航使用指南

## 快速开始

### 1. 准备工作

确保你已经使用 `slam_toolbox` 建好了地图。

### 2. 放置地图文件

将 slam_toolbox 生成的地图文件复制到 `maps/` 目录：

```bash
# 假设你的地图在 ~/.ros/ 目录下
cp ~/.ros/map.pgm /home/orin/revo_ros/src/revo_ugv_ros2/maps/
cp ~/.ros/map.yaml /home/orin/revo_ros/src/revo_ugv_ros2/maps/map.yaml
```

**重要**: 编辑 `maps/map.yaml` 确保 `image` 字段指向正确的地图文件。

### 3. 修改配置（根据实际机器人）

编辑 `config/nav2/nav2_params.yaml`，调整以下参数：

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `robot_radius` | 机器人半径 (米) | 0.3 |
| `max_vel_x` | 最大线速度 (m/s) | 0.5 |
| `max_vel_theta` | 最大角速度 (rad/s) | 1.0 |
| `inflation_radius` | 膨胀半径 (米) | 0.55 |

### 4. 构建项目

```bash
cd /home/orin/revo_ros
colcon build --packages-select revo_ugv_ros2
source install/setup.bash
```

---

## 启动导航

### 方法 1: 使用 Launch 文件（推荐）

```bash
# 启动导航栈
ros2 launch revo_ugv_ros2 revo_navigation.launch.py
```

这个命令会启动：
- Map Server (加载地图)
- AMCL (定位)
- Nav2 导航栈
- RViz2 (可视化)

### 方法 2: 分步启动

```bash
# 终端 1: 启动底盘和传感器
ros2 run revo_ugv_ros2 keyboard_control
ros2 run revo_ugv_ros2 revo_odom
# 激活激光雷达...

# 终端 2: 启动导航
ros2 launch revo_ugv_ros2 revo_navigation.launch.py
```

---

## 设置初始位姿

**第一次运行必须设置初始位姿！**

### 方法 1: 使用 RViz2

1. 打开 RViz2（启动导航时自动打开）
2. 点击顶部工具栏的 "2D Pose Estimate"
3. 在地图上点击机器人所在位置
4. 拖动鼠标设置朝向

### 方法 2: 使用测试代码

编辑 `revo_ugv_ros2/indoor_nav_test.py`，设置：

```python
use_initial_pose = True  # 改为 True
nav.set_initial_pose(x=0.0, y=0.0, theta=0.0)  # 修改为实际值
```

---

## 运行导航测试

### 基本用法

```bash
ros2 run revo_ugv_ros2 indoor_nav_test
```

### 选择测试场景

```bash
# 测试 1: 单个目标点导航
ros2 run revo_ugv_ros2 indoor_nav_test 1

# 测试 2: 多航点导航
ros2 run revo_ugv_ros2 indoor_nav_test 2

# 测试 3: 正方形模式导航
ros2 run revo_ugv_ros2 indoor_nav_test 3

# 运行所有测试
ros2 run revo_ugv_ros2 indoor_nav_test 4
```

### 修改目标点

编辑 `indoor_nav_test.py` 中的坐标：

```python
# test_single_goal 函数
target_x = 2.0  # 修改为目标点的 x 坐标
target_y = 1.0  # 修改为目标点的 y 坐标
target_theta = 0.0  # 修改为目标朝向 (弧度)
```

---

## Python API 使用

### 创建自定义导航脚本

```python
#!/usr/bin/env python3
import rclpy
from revo_ugv_ros2.indoor_nav_test import IndoorNavigator

def main():
    rclpy.init()
    nav = IndoorNavigator()
    nav.wait_for_nav2()

    # 设置初始位姿
    nav.set_initial_pose(0.0, 0.0, 0.0)

    # 导航到单个点
    nav.goto_pose(x=2.0, y=1.0, theta=0.0)

    # 或者导航多个航点
    waypoints = [
        (1.0, 0.0, 0.0),
        (2.0, 1.0, 1.57),
        (0.0, 0.0, 0.0),
    ]
    nav.goto_waypoints(waypoints)

    nav.navigator.lifecycleShutdown()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

---

## 故障排查

### 问题: 机器人不移动

- 检查 `/revo/cmd_vel` 是否有输出: `ros2 topic echo /revo/cmd_vel`
- 检查控制模式是否正确 (应该为 5 = SDK控制)
- 检查 `/odom` 是否正常发布

### 问题: 定位漂移

- 重新设置初始位姿
- 检查激光雷达数据质量
- 调整 AMCL 参数 (粒子数量)

### 问题: 导航失败

- 检查地图是否有动态障碍物
- 调整 `inflation_radius` 参数
- 减小 `max_vel_x` 和 `max_vel_theta`

---

## 文件结构

```
revo_ugv_ros2/
├── config/
│   └── nav2/
│       └── nav2_params.yaml      # 导航参数配置
├── launch/
│   └── revo_navigation.launch.py # 导航启动文件
├── revo_ugv_ros2/
│   └── indoor_nav_test.py        # 导航测试脚本
└── maps/
    ├── map.yaml                  # 地图配置
    ├── map.pgm                   # 地图图像
    └── map.yaml.example          # 配置示例
```

---

## 常用 ROS 2 命令

```bash
# 查看导航状态
ros2 topic echo /amcl_pose

# 发送导航目标 (命令行)
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 1.0, y: 0.0}}}}"

# 查看代价地图
ros2 topic echo /local_costmap/costmap
ros2 topic echo /global_costmap/costmap

# 重置代价地图
ros2 service call /clear_local_costmap nav2_msgs/srv/ClearEntireCostmap
ros2 service call /clear_global_costmap nav2_msgs/srv/ClearEntireCostmap
```
