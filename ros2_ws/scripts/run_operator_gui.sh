#!/bin/bash
set -e

source ~/mobile_robot/ai_ros_venv/bin/activate
source /opt/ros/humble/setup.bash
source ~/mobile_robot/ros2_ws/install/setup.bash

ros2 run amr_ai operator_gui
#~/mobile_robot/ros2_ws/scripts/run_operator_gui.sh


