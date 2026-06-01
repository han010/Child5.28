# System status subscription
# control_mode: 1-上锁, 2-遥控, 3-定速, 4-航线, 5-跟行, 6-SDK

std_msgs/Header header

uint8 control_mode
uint8[3] reserved          # 保留位

uint32 positioning_status  # 定位系统状态（按位解析）
uint32 battery_status      # 电池系统状态（按位解析）
uint32 chassis_status      # 底盘状态（按位解析）

uint32[8] motor_status     # 8 个电机状态数组（每项按位解析）
