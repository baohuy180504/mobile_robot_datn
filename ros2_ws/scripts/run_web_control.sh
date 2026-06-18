#!/bin/bash
# Khong dung "set -e": tool nay phai chay duoc ke ca khi ROS/workspace dang
# loi, nen moi buoc source ROS chi la best-effort, khong lam script dung
# giua duong.

source "$HOME/mobile_robot/ai_ros_venv/bin/activate" 2>/dev/null || true

# Best-effort: chi giup tinh nang canh bao "arduino_bridge dang chay" hoat
# dong, KHONG can thiet cho dieu khien Arduino qua serial.
source /opt/ros/humble/setup.bash 2>/dev/null || true
source "$HOME/mobile_robot/ros2_ws/install/setup.bash" 2>/dev/null || true
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Doi cong serial / mat khau / port web tai day neu can, khong sua code:
# export AMR_ARDUINO_SERIAL_PORT="/dev/arduino_mega"
# export AMR_CONTROL_PASSWORD="123"

echo "=== AMR EMERGENCY WEB CONTROL ==="
echo "Serial port : ${AMR_ARDUINO_SERIAL_PORT:-/dev/arduino_mega}"
echo "Web port    : 8090"

python3 "$HOME/mobile_robot/ros2_ws/src/amr_ai/amr_ai/web/web_control.py" --host 0.0.0.0 --port 8090