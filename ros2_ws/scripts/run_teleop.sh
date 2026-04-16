#!/bin/bash
echo "=== KEYBOARD ==="

source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 run teleop_twist_keyboard teleop_twist_keyboard
