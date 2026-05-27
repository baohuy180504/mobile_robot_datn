#!/bin/bash
set -e

tmux kill-session -t amr_web_rosbridge 2>/dev/null || true

echo "ROSBridge stopped."