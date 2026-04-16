#!/bin/bash
echo "=== SLAM TOOLBOX ==="

source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 launch amr_slam slam.launch.py
