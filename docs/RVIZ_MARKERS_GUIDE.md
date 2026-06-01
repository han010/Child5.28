# RViz 显示目标坐标点 - 快速指南

## 方法一：使用 Marker (推荐)

### 1. 运行示例脚本

```bash
cd /home/orin/Workspace/agri_ugv/ros2_ws
source install/setup.bash
python3 src/drivers/revo_ugv_ros2/revo_ugv_ros2/show_goal_marker.py
```

### 2. 在 RViz 中添加显示

启动 RViz：
```bash
rviz2
```

添加 Marker 显示：
1. 点击左下角 **Add** 按钮
2. 选择 **By topic** 标签
3. 找到 `/goal_marker` 或 `/goal_marker_array`
4. 点击 **OK**

或者使用预配置的 RViz 文件：
```bash
rviz2 -d src/drivers/revo_ugv_ros2/rviz/goal_markers.rviz
```

## 方法二：使用 Nav2 的 Goal Pose 工具

如果使用 Nav2 导航：

1. 在 RViz 工具栏中选择 **2D Goal Pose** 工具
2. 在地图上点击目标位置
3. 拖动设置目标方向
4. 松开鼠标发送目标

RViz 会自动显示一个绿色的箭头标记。

## 方法三：发布到 /goal_pose Topic

```python
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped

class GoalPublisher(Node):
    def __init__(self):
        super().__init__('goal_publisher')
        self.pub = self.create_publisher(PoseStamped, '/goal_pose', 10)

    def send_goal(self, x, y, theta=0.0):
        goal = PoseStamped()
        goal.header.frame_id = "map"
        goal.header.stamp = self.get_clock().now().to_msg()

        goal.pose.position.x = x
        goal.pose.position.y = y
        goal.pose.position.z = 0.0

        # 方向转四元数
        import tf_transformations
        q = tf_transformations.quaternion_from_euler(0, 0, theta)
        goal.pose.orientation.x = q[0]
        goal.pose.orientation.y = q[1]
        goal.pose.orientation.z = q[2]
        goal.pose.orientation.w = q[3]

        self.pub.publish(goal)
```

## Marker 类型参考

| 类型 | 说明 | 用途 |
|------|------|------|
| `ARROW` | 箭头 | 指向目标方向 |
| `CUBE` | 立方体 | 路径点 |
| `SPHERE` | 球体 | 目标点 |
| `CYLINDER` | 圆柱 | 区域标记 |
| `TEXT_VIEW_FACING` | 文本 | 标签 |
| `POINTS` | 点集 | 多个点 |
| `LINE_STRIP` | 线条 | 路径连线 |
| `MESH_RESOURCE` | 网格模型 | 3D 对象 |

## 颜色设置 (RGBA)

```python
# 红色
marker.color.r = 1.0
marker.color.g = 0.0
marker.color.b = 0.0
marker.color.a = 1.0  # 透明度 (0=透明, 1=不透明)

# 绿色
marker.color.r = 0.0
marker.color.g = 1.0
marker.color.b = 0.0
marker.color.a = 1.0

# 蓝色
marker.color.r = 0.0
marker.color.g = 0.0
marker.color.b = 1.0
marker.color.a = 1.0

# 黄色
marker.color.r = 1.0
marker.color.g = 1.0
marker.color.b = 0.0
marker.color.a = 1.0
```

## 坐标系说明

确保 `header.frame_id` 与你的环境匹配：

- `odom` - 里程计坐标系（Revo默认）
- `map` - 地图坐标系（SLAM/导航）
- `base_link` - 机器人坐标系

## 实时更新标记

要动态更新标记位置，只需重新发布相同 `ns` 和 `id` 的 Marker：

```python
# 更新位置
marker.pose.position.x = new_x
marker.pose.position.y = new_y
self.marker_pub.publish(marker)
```

## 删除标记

```python
marker.action = Marker.DELETE
self.marker_pub.publish(marker)
```

或删除所有标记：

```python
marker.action = Marker.DELETEALL
self.marker_pub.publish(marker)
```
