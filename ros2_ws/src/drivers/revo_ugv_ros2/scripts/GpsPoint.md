
source install/setup.bash
ros2 run revo_ugv_ros2 gps_waypoint_nav --ros-args \
  -p target_latitude:=30.2553593 \
  -p target_longitude:=120.2940436 \
  -p tolerance:=1.0 \
  -p linear_speed:=0.4 \
  -p angular_speed:=0.2

电梯口
latitude: 30.2553593
longitude: 120.2940436

斜路口
latitude: 30.2552692
longitude: 120.2940801

最远端
latitude: 30.2550618
longitude: 120.2940909


source install/setup.bash
ros2 run revo_ugv_ros2 gps_waypoint_nav --ros-args \
  -p target_latitude:=30.2549355 \
  -p target_longitude:=120.2942266 \
  -p tolerance:=1.0 \
  -p linear_speed:=0.5 \
  -p angular_speed:=0.1
