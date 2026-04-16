import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/huy_ubuntu/mobile_robot/ros2_ws/install/amr_ai'
