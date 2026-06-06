#!/bin/bash
set +e

SESSION=amr_operator
WS="$HOME/mobile_robot/ros2_ws"
LOG="/tmp/amr_operator_stack_stop.log"

{
  echo "=================================================="
  echo "$(date) - STOP AMR OPERATOR STACK"
  echo "=================================================="

  cd "$WS" 2>/dev/null || true

  source "$HOME/mobile_robot/ai_ros_venv/bin/activate" 2>/dev/null || true
  source /opt/ros/humble/setup.bash 2>/dev/null || true
  source "$WS/install/setup.bash" 2>/dev/null || true

  export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"
  export ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-0}"
  export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}"

  echo "[1/4] Stop follow mode..."
  timeout 2 ros2 service call /amr_ai/set_mode amr_interfaces/srv/SetAiMode "{mode: 0, command: 'STOP_FOLLOW'}" >/dev/null 2>&1 || true

  echo "[2/4] Publish zero velocity..."
  for i in 1 2 3 4 5; do
    timeout 1 ros2 topic pub /cmd_vel_safe geometry_msgs/msg/Twist "{}" --once >/dev/null 2>&1 || true
    timeout 1 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{}" --once >/dev/null 2>&1 || true
    sleep 0.05
  done

  echo "[3/4] Kill tmux session: ${SESSION}"
  tmux kill-session -t "${SESSION}" 2>/dev/null || true

  sleep 0.5

  echo "[4/4] Publish zero velocity after kill..."
  for i in 1 2 3; do
    timeout 1 ros2 topic pub /cmd_vel_safe geometry_msgs/msg/Twist "{}" --once >/dev/null 2>&1 || true
    timeout 1 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{}" --once >/dev/null 2>&1 || true
    sleep 0.05
  done

  echo "[OK] AMR operator stack stopped."
} 2>&1 | tee -a "$LOG"
