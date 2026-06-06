#!/bin/bash
echo "=== SLAM TOOLBOX ==="

source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch amr_slam fusion_slam.launch.py enable_octomap:=true
