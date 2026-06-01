# GPS 直连导航（gps_nav_direct）排错记录

> 日期：2026-05-09
> 环境：ROS2 Humble, Jetson Orin, XAG Revo R100, RPLIDAR A1 (20m)
> 架构：`/revo/pose` → `gps_to_odom_node` → `/gps_odom` → Nav2（无 EKF/navsat 中间层）

---

## 背景与目标

绕过 `navsat_transform_node` + 双 EKF 的复杂架构，直接将 Revo SDK 的融合 GPS/RTK/IMU 数据（`/revo/pose`）转换为标准里程计（`/gps_odom`），配合 Nav2 实现室外无地图 GPS 导航。

**数据流**：
```
/revo/pose (PoseState)
  → gps_to_odom_node
    → /gps_odom (Odometry) + TF(odom→base_link) + /gps_origin
      → Nav2 (map=odom via 静态 TF)
        → /cmd_vel
          → cmd_vel_relay → /revo/cmd_vel
```

---

## 问题 1：坐标系转换 — ENU vs 自定义

### 现象

车头朝北时，odom 显示 yaw=0°，前方箭头沿 X 轴（红色）指向北方。但 ROS ENU 标准要求：
- X 轴(红) = 东, Y 轴(绿) = 北
- yaw=0° 时车头朝东, yaw=+90° 时车头朝北

### 根因

两种坐标系约定混淆：

| 属性 | GPS/Revo 罗盘 | ROS ENU (REP-103/105) |
|------|-------------|----------------------|
| 0° 方向 | 北 | 东 (+X) |
| 90° 方向 | 东 | 北 (+Y) |
| 正方向 | 顺时针 (CW) | 逆时针 (CCW) |

早期代码直接用 `yaw = -revo_yaw`（仅取反 CW→CCW），并将 GPS 坐标设为 X=北、Y=东，这违反了 ROS ENU 标准。

### 正确的转换公式

**GPS → ENU 局部坐标**：
```python
def _gps_to_local(lat, lon, lat0, lon0):
    lat0_rad = lat0 * _DEG2RAD
    north = (lat - lat0) * _DEG2RAD * _EARTH_RADIUS       # 纬度差 → 北
    east  = (lon - lon0) * _DEG2RAD * _EARTH_RADIUS * cos(lat0_rad)  # 经度差 → 东
    return east, north   # X=东, Y=北
```

**Revo heading → ROS yaw**：
```python
yaw_revo_raw = float(msg.yaw) / 1000.0   # CW+, 0=北
yaw = -yaw_revo_raw + math.pi / 2.0      # CCW+, 0=东
```

数学等价：`ROS_yaw = π/2 - GPS_heading`

验证：
- GPS=0°(北) → ROS=+90°(北/Y+) ✓
- GPS=90°(东) → ROS=0°(东/X+) ✓
- GPS=180°(南) → ROS=-90°(南/Y-) ✓

### 修改文件

- `rob_localization_pkg/gps_to_odom_node.py` — GPS 转换 + yaw 公式
- `gps_nav2/gps_nav_goal.py` — 目标点转换使用相同 ENU 公式

---

## 问题 2：colcon build 安装目录错误 — 运行旧代码

### 现象

源码文件内容已修改正确，但运行时节点仍使用旧逻辑（yaw 没有 +π/2）。`/gps_odom` 输出的 yaw 与代码不一致。

### 根因

`colcon build` 在 `/home/orin/Workspace/agri_ugv/` 根目录执行，而非 `ros2_ws/` 目录。项目根目录下也有 `build/` 和 `install/` 子目录（含 COLCON_IGNORE），colcon 将包安装到了：
- `/home/orin/Workspace/agri_ugv/install/rob_localization/` （错误）
- 而非 `/home/orin/Workspace/agri_ugv/ros2_ws/install/rob_localization/` （正确）

运行 `source ros2_ws/install/setup.bash` 时加载的是旧版本。

### 修复

```bash
# 1. 清理错误位置的构建产物
rm -rf /home/orin/Workspace/agri_ugv/build/gps_nav2
rm -rf /home/orin/Workspace/agri_ugv/build/rob_localization
rm -rf /home/orin/Workspace/agri_ugv/install/gps_nav2
rm -rf /home/orin/Workspace/agri_ugv/install/rob_localization

# 2. 在正确目录下重建
cd /home/orin/Workspace/agri_ugv/ros2_ws
colcon build --packages-select rob_localization gps_nav2 --symlink-install
```

### 预防

在 `CLAUDE.md` 中已添加醒目警告：**colcon build 必须在 `ros2_ws/` 目录下执行**。

---

## 问题 3：`latch=True` 在 ROS2 rclpy 不支持

### 现象

```
TypeError: Node.create_publisher() got an unexpected keyword argument 'latch'
```

### 根因

ROS1 的 `latch=True`（新订阅者收到最后一条消息）在 ROS2 中通过 QoS 策略实现。

### 修复

```python
from rclpy.qos import QoSProfile, DurabilityPolicy

self._origin_pub = self.create_publisher(
    Point, '/gps_origin',
    QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL)
)
```

订阅端也需要匹配的 QoS：
```python
self.origin_sub = self.create_subscription(
    Point, '/gps_origin', self.origin_callback,
    QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL)
)
```

---

## 问题 4：BehaviorTree.CPP 版本不兼容

### 现象

```
[ERROR] [BehaviorTreeEngine]: Node not recognized: RecoveryNode
[ERROR] [BehaviorTreeEngine]: Node not recognized: PipelineSequence
```

### 根因

系统安装的 BehaviorTree.CPP 版本较旧，不支持 `RecoveryNode`、`PipelineSequence` 等高级节点。Nav2 Humble 默认的 BT XML 文件使用了这些节点。

### 修复

创建自定义 BT XML（`config/nav2/gps_nav_bt.xml`），仅使用基础节点：

```xml
<root main_tree_to_execute="MainTree">
  <BehaviorTree ID="MainTree">
    <Sequence name="Navigate">
      <ComputePathToPose goal="{goal}" path="{path}" planner_id="GridBased"/>
      <FollowPath path="{path}" controller_id="FollowPath"/>
    </Sequence>
  </BehaviorTree>
</root>
```

配置中指定自定义 BT：
```yaml
bt_navigator:
  ros__parameters:
    default_nav_to_pose_bt_xml: "$(find-pkg-share gps_nav2)/config/nav2/gps_nav_bt.xml"
```

---

## 问题 5：Nav2 `/cmd_vel` 话题硬编码

### 现象

Nav2 controller_server 输出速度到 `/cmd_vel`，但 Revo 底盘监听 `/revo/cmd_vel`。Nav2 Humble 的 `cmd_vel` 话题名不可通过参数配置。

### 修复

创建 `cmd_vel_relay.py` 中继节点：

```python
class CmdVelRelay(Node):
    def __init__(self):
        super().__init__('cmd_vel_relay')
        self.create_subscription(Twist, '/cmd_vel', self._relay, 10)
        self._pub = self.create_publisher(Twist, '/revo/cmd_vel', 10)

    def _relay(self, msg: Twist):
        self._pub.publish(msg)
```

> 注：尝试使用 `topic_tools relay` 但系统未安装该包。

---

## 问题 6：Costmap "No valid trajectories" — inflation_radius < robot_radius

### 现象

```
[WARN] [dwb_controller]: No valid trajectories found
```

机器人只能以极低速（0.1 m/s）移动或完全不动。

### 根因

`inflation_radius`（0.4m / 0.55m）小于 `robot_radius`（0.65m）。机器人的内切圆半径为 0.65m，costmap 认为机器人始终与障碍物碰撞，DWB 找不到有效轨迹。

### 修复

```yaml
local_costmap:
  local_costmap:
    ros__parameters:
      robot_radius: 0.65
      inflation_layer:
        inflation_radius: 1.0   # 必须 > robot_radius (0.65)

global_costmap:
  global_costmap:
    ros__parameters:
      robot_radius: 0.65
      inflation_layer:
        inflation_radius: 1.0   # 必须 > robot_radius (0.65)
```

---

## 问题 7：Costmap "Sensor origin out of map bounds"

### 现象

```
[WARN] [local_costmap]: Sensor origin at (-0.36, -0.17 0.20) is out of map bounds
       (0.60, -5.30, 0.00) to (10.55, 4.65, 0.78)
```

GPS 位置在 0.2s 内跳变约 5m，rolling window costmap 来不及重定位。

### 根因

1. GPS 融合位置存在突变（RTK 修正、信号恢复等）
2. Local costmap 仅 6m × 6m，rolling window 重定位跟不上 5m 跳变
3. Global costmap 100m × 0.05m = 400 万格，计算负担过重

### 修复

**Local costmap**（匹配 20m 雷达探测距离 + 容忍 GPS 跳变）：

| 参数 | 旧值 | 新值 | 原因 |
|------|------|------|------|
| width/height | 6m | 20m | 匹配雷达探测距离，容忍 GPS 跳动 |
| update_frequency | 5Hz | 10Hz | 更快更新应对 GPS 跳变 |
| transform_tolerance | 无 | 2.0s | 容忍 GPS 位置跳变 |
| raytrace_max_range | 5m | 10m | local 避障探测距离 |
| obstacle_max_range | 4.5m | 9.5m | 配合 raytrace |

**Global costmap**（室外规划用）：

| 参数 | 旧值 | 新值 | 原因 |
|------|------|------|------|
| width/height | 100m | 50m | 仍足够覆盖导航目标 |
| resolution | 0.05m | 0.2m | 从 400 万格降到 6.25 万格 |
| transform_tolerance | 无 | 2.0s | 容忍 GPS 位置跳变 |
| raytrace_max_range | 10m | 20m | 匹配雷达探测距离 |
| obstacle_max_range | 9m | 18m | 充分利用雷达探测能力 |

---

## 问题 8：Planner Server 超时 — "Timed out waiting for action server"

### 现象

```
[WARN] [bt_navigator]: Timed out while waiting for action server to acknowledge
       goal request for compute_path_to_pose
[ERROR] [bt_navigator]: Goal failed
```

### 根因

`expected_planner_frequency: 20.0` 让 planner_server 以 20Hz 连续规划（无目标时也空转），可能阻塞 action server 无法响应新请求。

### 修复

```yaml
planner_server:
  ros__parameters:
    expected_planner_frequency: 0.0   # 按需规划，不连续空转
```

同时增大 BT navigator 的 action 超时：
```yaml
bt_navigator:
  ros__parameters:
    default_server_timeout: 100   # 原 20，增大到 100
```

---

## 问题 9：QoS 不匹配 — /gps_origin 订阅收不到数据

### 现象

`gps_nav_goal.py` 的 `/gps_origin` 回调从未触发，`gps_initialized` 始终为 False。

### 根因

发布端使用 `TRANSIENT_LOCAL` durability，订阅端使用默认 `VOLATILE`。ROS2 要求发布端和订阅端的 QoS durability 兼容。

### 修复

订阅端匹配 QoS：
```python
self.origin_sub = self.create_subscription(
    Point, '/gps_origin', self.origin_callback,
    QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL)
)
```

---

## 最终配置文件清单

| 文件 | 用途 |
|------|------|
| `rob_localization_pkg/gps_to_odom_node.py` | GPS→Odom 转换（ENU, yaw=π/2-heading） |
| `rob_localization_pkg/cmd_vel_relay.py` | /cmd_vel → /revo/cmd_vel 中继 |
| `launch/gps_nav_direct.launch.py` | GPS 直连导航启动文件 |
| `gps_nav2/gps_nav_goal.py` | GPS 目标点服务节点 |
| `config/nav2/gps_nav_bt.xml` | 自定义行为树（兼容旧版 BT） |
| `config/nav2/nav2_params_gps.yaml` | Nav2 GPS 导航参数 |
| `setup.py` | 入口点：gps_to_odom, cmd_vel_relay |

## 经验总结

1. **坐标系必须严格遵循 ROS ENU 标准**（X=东, Y=北, yaw 东=0），不能自创约定，否则 Nav2 所有组件行为异常
2. **colcon build 必须在 `ros2_ws/` 目录下执行**，否则安装到错误路径，运行旧代码
3. **inflation_radius 必须大于 robot_radius**，否则 costmap 认为机器人始终碰撞
4. **GPS 跳变**可通过增大 costmap 尺寸、提高 update_frequency、增大 transform_tolerance 来缓解
5. **ROS2 QoS 必须匹配**：TRANSIENT_LOCAL 发布者需要 TRANSIENT_LOCAL 订阅者
6. **BehaviorTree.CPP 版本差异**：Humble 默认 BT 可能包含旧版不支持的节点，需自定义最小 BT
7. **Nav2 Humble 的 `cmd_vel` 话题硬编码**：需要中继节点转发到实际控制话题
8. **`expected_planner_frequency: 0.0`** 是 GPS 导航场景的推荐设置，避免 planner 空转阻塞 action
