#!/bin/bash
set -e

WS="$HOME/mobile_robot/ros2_ws"

cd "$WS"

source "$HOME/mobile_robot/ai_ros_venv/bin/activate" 2>/dev/null || true
source /opt/ros/humble/setup.bash
source install/setup.bash

echo "=== AMR ALERT WEB STREAM ==="
echo "Input : /amr_ai/debug/alert/image"
echo "Output: /amr_ai/debug/alert/image_web/compressed"
echo "Config: 400x270, 8 FPS, JPEG quality 60"

python3 "$WS/scripts/web_camera_low_latency.py" \
  --input /amr_ai/debug/alert/image \
  --output /amr_ai/debug/alert/image_web/compressed \
  --width 400 \
  --height 270 \
  --fps 8 \
  --quality 60
