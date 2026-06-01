# GPS导航状态消息
# 发布当前GPS导航任务的状态信息

# 导航状态
std_msgs/Header header
string status              # 状态类型: "idle", "navigating", "paused", "completed", "failed"
string message             # 状态描述信息

# 航点信息
int32 current_waypoint     # 当前航点索引 (从1开始)
int32 total_waypoints      # 总航点数
bool is_looping            # 是否循环模式

# 位置信息
float64 current_latitude   # 当前纬度
float64 current_longitude  # 当前经度
float64 target_latitude    # 目标纬度
float64 target_longitude   # 目标经度
float64 distance_to_goal   # 距离目标的距离(米)

# 进度信息
float32 progress_percent   # 任务进度百分比 (0.0 - 100.0)
builtin_interfaces/Duration estimated_time_remaining  # 预计剩余时间
