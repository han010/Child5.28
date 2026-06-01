cmake_minimum_required(VERSION 3.5)
project(gps_nav2)

# Default to C++17
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)

# 生成服务和消息接口
rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/GPSGoal.srv"
  "srv/GPSWaypointNav.srv"
  "srv/GPSNavControl.srv"
  "msg/GPSWaypoint.msg"
  "msg/NavGoalStatus.msg"
  DEPENDENCIES std_msgs geometry_msgs sensor_msgs nav_msgs
)

# 手动安装Python模块（避免与rosidl目标冲突）
install(DIRECTORY gps_nav2/
  DESTINATION lib/python3.10/dist-packages/gps_nav2
)

# 安装 Python 入口脚本
install(PROGRAMS
  gps_nav2/gps_nav_goal.py
  DESTINATION lib/${PROJECT_NAME}
)

# 安装配置文件和launch文件
install(DIRECTORY
  config
  launch
  DESTINATION share/${PROJECT_NAME}
)

# 安装resource和package.xml
install(FILES package.xml
  DESTINATION share/${PROJECT_NAME}
)
install(FILES resource/gps_nav2
  DESTINATION share/ament_index/resource_index/packages
)

# 测试
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_export_dependencies(rosidl_default_runtime)
ament_package()
