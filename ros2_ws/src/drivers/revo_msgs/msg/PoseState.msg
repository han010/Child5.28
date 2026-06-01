# Pose state subscription
# 注意：实际物理值需按下列缩放恢复，例如 longitude_deg = longitude / 1e7

# Header
std_msgs/Header header

# 经纬度，单位：1/10000000 度
int32 longitude         # 原始值，实际经度 = longitude / 1e7 (deg)
int32 latitude          # 原始值，实际纬度 = latitude / 1e7 (deg)

# 高程，单位：1/10 米
int16 altitude          # 实际高度 = altitude / 10.0 (m)

# 姿态角，单位：1/1000 弧度
int16 roll              # 实际 roll = roll / 1000.0 (rad)
int16 pitch             # 实际 pitch = pitch / 1000.0 (rad)
int16 yaw               # 实际 yaw = yaw / 1000.0 (rad)

# 线/角速度
# 融合线速度，单位：1/100 m/s
int16 fused_linear_velocity    # 实际 = fused_linear_velocity / 100.0 (m/s)

# 融合角速度，单位：1/1000 rad/s
int16 fused_angular_velocity   # 实际 = fused_angular_velocity / 1000.0 (rad/s)

# 轮速线/角速度
int16 wheel_linear_velocity    # 单位：1/100 m/s, 实际 = wheel_linear_velocity / 100.0 (m/s)
int16 wheel_angular_velocity   # 单位：1/1000 rad/s, 实际 = wheel_angular_velocity / 1000.0 (rad/s)
