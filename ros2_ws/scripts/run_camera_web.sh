#!/bin/bash
set -e

WS="$HOME/mobile_robot/ros2_ws"

cd "$WS"

source "$HOME/mobile_robot/ai_ros_venv/bin/activate" 2>/dev/null || true
source /opt/ros/humble/setup.bash
source install/setup.bash

echo "=== AMR CAMERA WEB STREAM ==="
echo "Input : /camera/color/image_raw"
echo "Output: /camera/color/image_web/compressed"
echo "Config: 640x360, 12 FPS, JPEG quality 60"

python3 "$WS/scripts/web_camera_low_latency.py" \
  --input /camera/color/image_raw \
  --output /camera/color/image_web/compressed \
  --width 640 \
  --height 360 \
  --fps 12 \
  --quality 60
