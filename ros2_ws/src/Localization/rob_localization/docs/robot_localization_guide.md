# Robot Localization 集成指南

## 概述

本文档描述如何为 Revo UGV 集成 `robot_localization` 包，实现多传感器融合定位。

当前状态：**框架搭建中**，IMU 数据适配已完成，EKF 配置和 launch 文件待完成。

---

## 1. 安装 robot_localization

`robot_localization` 是官方 ROS2 包（C++ 实现），无需自行编译，直接安装：

```bash
sudo apt install ros-humble-robot-localization
```

安装后会提供以下节点：
- `ekf_node` — 扩展卡尔曼滤波器
- `ukf_node` — 无迹卡尔曼滤波器
- `navsat_transform_node` — GPS 坐标转换

> **本项目不需要 `src/Localization/rob_localization/` 下的 Python 包编译官方包**。
> 该 Python 包仅用于存放我们自己的配置文件、launch 文件和辅助脚本。

---

## 2. 系统架构

### 2.1 室内模式（无 GPS）

单 EKF 实例，融合轮式里程计 + IMU：

```
Revo SDK (50ms/20Hz)
  └─ revo_bridge_node
       ├─ /revo/pose     (PoseState)    ──→  revo_odom_node ──→ /odom (Odometry)
       └─ /revo/imu      (Imu)          ──→  ekf_node ─────────→ /odometry/filtered
                                                     ↑                + TF: odom→base_footprint
                                              /odom (Odometry)
```

### 2.2 室外模式（带 GPS）

双 EKF 实例 + navsat_transform_node：

```
Revo SDK (50ms/20Hz)
  └─ revo_bridge_node
       ├─ /revo/pose     (PoseState)    ──→  revo_odom_node ──→ /odom
       ├─ /revo/imu      (Imu)          ──┐
       └─ (GPS via /revo/pose)           │
                                        ├─→ ekf_local (odom帧)
                                        │     world_frame: odom
                                        │     输出: odom → base_footprint TF
                                        │
                                        ├─→ navsat_transform_node
                                        │     输入: /gps/fix + /odometry/filtered + /revo/imu
                                        │     输出: /gps/odom (Odometry, map坐标系)
                                        │
                                        └─→ ekf_global (map帧)
                                              world_frame: map
                                              输入: /gps/odom
                                              输出: map → odom TF
```

---

## 3. 已完成的适配工作

### 3.1 IMU 数据适配 ✅

**文件**: `ros2_ws/src/drivers/revo_ugv_ros2/revo_ugv_ros2/revo_bridge_node.py`

在 `revo_bridge_node` 中新增了 `/revo/imu` 话题，将 SDK 的 PoseData 转换为标准 `sensor_msgs/Imu`：

| 字段 | 数据来源 | 备注 |
|------|----------|------|
| orientation (四元数) | roll, pitch, yaw | yaw 取反 (CW→CCW) |
| angular_velocity.z | fused_angular_velocity | 取反 (CW→CCW) |
| angular_velocity.x/y | 无数据 | 设为 0 |
| linear_acceleration | 无数据 | 协方差设 -1 (REP-145) |

**发布频率**: 20Hz（与 SDK 推送频率一致）

### 3.2 配置文件 ✅

- `params/ekf_reference.yaml` — EKF 参数参考（含中文注释）
- `config/revo_bridge_config.json` — 新增 `imu_frame_id: base_link`

---

## 4. 待完成工作

### 4.1 编写实际 EKF 配置文件

基于 `ekf_reference.yaml`，创建实际使用的配置文件。

**室内配置** (`params/ekf_indoor.yaml`)：

```yaml
ekf_filter_node:
    ros__parameters:
        frequency: 30.0
        sensor_timeout: 0.1
        two_d_mode: true
        publish_tf: true

        # 坐标系 — 注意 Revo 使用 base_footprint
        odom_frame: odom
        base_link_frame: base_footprint
        world_frame: odom

        # 数据源1: 轮式里程计 (来自 revo_odom_node)
        odom0: /odom
        odom0_config: [false, false, false,   # 位姿不融合（EKF自己积分更准）
                       false, false, false,
                       true,  false, false,   # vx: 轮速计线速度
                       false, false, true,    # vyaw: 角速度
                       false, false, false]
        odom0_queue_size: 2
        odom0_differential: false
        odom0_relative: false

        # 数据源2: IMU (来自 revo_bridge_node)
        imu0: /revo/imu
        imu0_config: [false, false, false,   # 无位置
                      true,  true,  false,   # roll, pitch (2D模式下被忽略)
                      false, false, false,
                      false, false, true,    # vyaw: IMU 角速度
                      false, false, false]   # 无加速度
        imu0_queue_size: 5
        imu0_differential: false
        imu0_relative: true                  # 从当前位置开始
```

**室外配置** (`params/ekf_outdoor.yaml`)：需要双 EKF + navsat_transform，后续完成。

### 4.2 编写 launch 文件

在 `src/Localization/rob_localization/launch/` 下创建：

- `ekf_indoor.launch.py` — 室内定位（单 EKF）
- `ekf_outdoor.launch.py` — 室外定位（双 EKF + GPS）

需要修改 `setup.py` 的 `data_files` 和 `entry_points`。

### 4.3 修改 setup.py 安装配置文件

当前 `setup.py` 未安装 `params/` 和 `launch/` 目录，需要补充：

```python
import os
from glob import glob

setup(
    ...
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/robot_localization']),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'params'), glob('params/*.yaml')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    ...
)
```

### 4.4 修改 revo_odom_node 避免重复发布 TF

当前 `revo_odom_node` 同时发布 `/odom` 话题和 `odom→base_footprint` TF。
集成 EKF 后，TF 应由 EKF 负责发布（更准确），需要给 odom_node 加一个开关：

```python
self.declare_parameter('publish_tf', True)  # 默认保持兼容
```

当 EKF 启动时，设置 `publish_tf: false` 避免冲突。

### 4.5 室外 GPS 集成（navsat_transform_node）

需要额外工作：

1. **确认 GPS 数据格式**：`revo_gnss_node` 发布 `sensor_msgs/NavSatFix` → 满足要求
2. **navsat_transform_node 配置**：需要 IMU + Odometry + NavSatFix 三个输入
3. **双 EKF 实例**：
   - 局部 EKF (`ekf_local`)：world_frame=odom，融合轮速+IMU
   - 全局 EKF (`ekf_global`)：world_frame=map，融合 GPS 转换后的里程计
4. **坐标系关系**：`map → odom → base_footprint → base_link → ...`

### 4.6 协方差调参

初始值不需要精确，后续根据实际运行情况调整：

| 调参场景 | 操作 |
|----------|------|
| 位置估计滞后 | 增大 `process_noise_covariance` 对应变量 |
| 估计值抖动 | 增大传感器 `rejection_threshold` |
| 转弯时估计不准 | 检查 IMU angular_velocity.z 协方差 |
| GPS 跳变 | 降低 GPS 权重或使用 `differential: true` |

---

## 5. 构建和测试

### 5.1 构建

```bash
cd /home/orin/Workspace/agri_ugv/ros2_ws
colcon build --packages-select robot_localization
source install/setup.bash
```

### 5.2 测试步骤

**第一步：验证 IMU 数据**

```bash
# 终端1: 启动底盘
ros2 launch revo_ugv_ros2 revo_chassis.launch.py

# 终端2: 查看 IMU 话题
ros2 topic echo /revo/imu

# 检查：
# - orientation 四元数是否合理（静止时接近 [0,0,0,1]）
# - angular_velocity.z 旋转时是否变化
# - header.frame_id 是否为 "base_link"
```

**第二步：启动 EKF（室内）**

```bash
# 终端1: 底盘
ros2 launch revo_ugv_ros2 revo_chassis.launch.py

# 终端2: 传感器
ros2 launch revo_ugv_ros2 revo_sensors.launch.py

# 终端3: EKF
ros2 launch rob_localization ekf_indoor.launch.py

# 终端4: 可视化
rviz2
# 添加 Odometry 显示，话题选 /odometry/filtered
```

**第三步：对比验证**

```bash
# 同时监听原始里程计和 EKF 输出
ros2 topic echo /odom --field header.stamp &
ros2 topic echo /odometry/filtered --field header.stamp

# 控制机器人移动，观察：
# - EKF 输出是否更平滑
# - 转弯时方向估计是否更准确
# - TF 树是否正确: odom → base_footprint
```

---

## 6. 文件结构规划

```
ros2_ws/src/Localization/rob_localization/
├── docs/
│   └── robot_localization_guide.md   ← 本文档
├── params/
│   ├── ekf_reference.yaml           ← 参数参考（带中文注释）
│   ├── ekf_indoor.yaml              ← 室内 EKF 配置
│   └── ekf_outdoor.yaml             ← [待创建] 室外 EKF 配置
├── launch/
│   ├── ekf_indoor.launch.py         ← 室内定位 launch
│   └── ekf_outdoor.launch.py        ← [待创建] 室外定位 launch
├── rob_localization_pkg/
│   └── __init__.py
├── package.xml
├── setup.py
└── setup.cfg
```

---

## 7. 参考资源

- [robot_localization 官方文档](https://docs.ros.org/en/humble/p/robot_localization/)
- [REP-105: 坐标系约定](https://www.ros.org/reps/rep-0105.html)
- [REP-145: IMU 数据约定](https://www.ros.org/reps/rep-0145.html)
- 项目坐标系说明: `CLAUDE.md` → 坐标系约定章节
