#!/bin/bash
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch amr_description gazebo.launch.py
