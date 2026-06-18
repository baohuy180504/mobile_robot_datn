#!/bin/bash
set -e

source ~/mobile_robot/ai_ros_venv/bin/activate
source /opt/ros/humble/setup.bash
source ~/mobile_robot/ros2_ws/install/setup.bash

# Ghi log ra file để xem lại được kể cả khi chạy bằng icon (Terminal=false
# làm mất hết output). Vẫn hiện trực tiếp trên terminal nếu chạy tay qua SSH.
export ROS_DOMAIN_ID=0
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
LOG_FILE="/tmp/operator_gui.log"
echo "===== operator_gui start $(date) =====" >> "$LOG_FILE"
env >> "$LOG_FILE"
echo "=====" >> "$LOG_FILE"

ros2 run amr_ai operator_gui 2>&1 | tee -a "$LOG_FILE"
#~/mobile_robot/ros2_ws/scripts/run_operator_gui.sh