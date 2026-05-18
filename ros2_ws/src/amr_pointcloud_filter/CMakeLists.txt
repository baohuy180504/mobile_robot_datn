cmake_minimum_required(VERSION 3.8)
project(amr_pointcloud_filter)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic -O3)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
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

install(TARGETS
  depth_cloud_filter
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()