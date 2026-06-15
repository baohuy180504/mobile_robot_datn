cmake_minimum_required(VERSION 3.8)
project(amr_pointcloud_filter)

if(POLICY CMP0074)
  cmake_policy(SET CMP0074 NEW)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic -O3)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(pcl_conversions REQUIRED)
find_package(PCL REQUIRED COMPONENTS common filters)

include_directories(
  ${PCL_INCLUDE_DIRS}
)

link_directories(
  ${PCL_LIBRARY_DIRS}
)

add_definitions(${PCL_DEFINITIONS})

add_executable(depth_cloud_filter src/depth_cloud_filter.cpp)

ament_target_dependencies(depth_cloud_filter
  rclcpp
  sensor_msgs
  pcl_conversions
)

target_link_libraries(depth_cloud_filter
  ${PCL_LIBRARIES}
)

add_executable(height_risk_projector src/height_risk_projector.cpp)

ament_target_dependencies(height_risk_projector
  rclcpp
  sensor_msgs
  nav_msgs
  geometry_msgs
  tf2
  tf2_ros
  tf2_geometry_msgs
)

install(TARGETS
  depth_cloud_filter
  height_risk_projector
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
