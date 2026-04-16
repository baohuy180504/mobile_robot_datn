#!/bin/bash
echo "=== EXPLORE MODE (GAZEBO SIMULATION) ==="
killall -9 gzserver gzclient rviz2 > /dev/null 2>&1
cd ~/test_ros/ros2_ws
colcon build --symlink-install --packages-select amr_navigation amr_description
source /opt/ros/humble/setup.bash
source install/setup.bash

# Gọi file Launch tổng từ package amr_navigation
ros2 launch amr_navigation auto_slam.launch.py