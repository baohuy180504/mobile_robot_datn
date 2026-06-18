cmake_minimum_required(VERSION 3.8)
project(amr_costmap_plugins)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(nav2_costmap_2d REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(pluginlib REQUIRED)
find_package(tf2 REQUIRED)

set(dependencies
  rclcpp
  nav2_costmap_2d
  nav_msgs
  pluginlib
  tf2
)

include_directories(include)

add_library(amr_costmap_plugins SHARED
  src/ghrf_layer.cpp
)

ament_target_dependencies(amr_costmap_plugins
  ${dependencies}
)

# Đăng ký GHRFLayer với pluginlib để Nav2 costmap_2d nạp được qua tên class
# "amr_costmap_plugins::GHRFLayer" khai báo trong nav2_params_fusion.yaml.
pluginlib_export_plugin_description_file(nav2_costmap_2d costmap_plugins.xml)

install(
  TARGETS amr_costmap_plugins
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(
  DIRECTORY include/
  DESTINATION include
)

install(
  FILES costmap_plugins.xml
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_export_include_directories(include)
ament_export_libraries(amr_costmap_plugins)
ament_export_dependencies(${dependencies})

ament_package()