import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/huyjetson/mobile_robot/ros2_ws/src/amr_bringup/install/amr_bringup'
