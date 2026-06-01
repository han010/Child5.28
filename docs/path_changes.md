# 路径变更清单

## 目录重组映射

| 旧路径 | 新路径 |
|--------|--------|
| `src/hunter_ros2/` | `src/drivers/hunter_ros2/` |
| `src/revo_msgs/` | `src/drivers/revo_msgs/` |
| `src/revo_ugv_ros2/` | `src/drivers/revo_ugv_ros2/` |
| `src/ugv_sdk/` | `src/drivers/ugv_sdk/` |
| `src/rplidar_ros/` | `src/sensors/rplidar_ros/` |
| `src/serial_ros2/` | `src/sensors/serial_ros2/` |
| `src/wheeltec_radar/` | `src/sensors/wheeltec_radar/` |
| `src/wheeltec_gps/` | `src/sensors/wheeltec_gps/` |
| `src/astra_cam/` | `src/sensors/astra_cam/` |
| `src/yolo-v8/` | `src/perception/yolo-v8/` |

---

## 一、需要修改路径的文件（1处）

### 1. YOLO测试脚本 - 硬编码绝对路径
- **文件**: `src/perception/yolo-v8/yolo_ros/yolo_ros/test_msgs.py`
- **行号**: 313
- **旧**: `'/home/orin/Workspace/agri_ugv/ros2_ws/src/yolo-v8/yolo_ros/model/yolov8n.engine'`
- **新**: `'/home/orin/Workspace/agri_ugv/ros2_ws/src/perception/yolo-v8/yolo_ros/model/yolov8n.engine'`

---

## 二、需要修复格式的srv文件（3处）

### 1. GPSGoal.srv - 缺少 `---` 分隔符
- **文件**: `src/planning/gps_nav2/srv/GPSGoal.srv`
- **问题**: 请求和响应之间缺少 `---` 分隔符

### 2. GPSWaypointNav.srv - 格式错误
- **文件**: `src/planning/gps_nav2/srv/GPSWaypointNav.srv`
- **问题**: 结构混乱，嵌套类型定义和srv格式混杂

### 3. GPSNavControl.srv - 缺少 `---` 分隔符
- **文件**: `src/planning/gps_nav2/srv/GPSNavControl.srv`
- **问题**: 请求和响应之间缺少 `---` 分隔符

---

## 三、不需要修改的文件（确认清单）

以下文件经检查后确认**不需要修改**：

### ROS2 包管理系统自动处理的
- 所有 `package.xml` 中的依赖声明（使用包名而非路径）
- 所有 `CMakeLists.txt` 中的相对路径引用（相对于包自身目录）
- 所有 `setup.py` 中的数据文件路径（使用 `glob()` 相对路径）
- 所有 launch 文件（使用 `get_package_share_directory()` 动态查找包）

### Python/C++ import
- `from xa_revosdk_ugv import ...` （由 `REVO_SDK_ROOT` 环境变量控制，不在 ros2_ws 内）
- `from revo_msgs.msg import ...` （使用 ROS 包名）
- `#include "ugv_sdk/..."` （C++ 通过 CMake find_package 解析）
- `#include "hunter_msgs/..."` （同上）

### 环境变量/脚本
- `setup_env.sh` 中的 `REVO_SDK_ROOT` 指向外部 SDK 目录，不影响

### 文档中的示例路径（可选更新）
- `src/drivers/revo_ugv_ros2/docs/NAVIGATION_GUIDE.md` - 示例路径（不影响功能）
- `src/drivers/hunter_ros2/README.md` - 示例路径（不影响功能）
