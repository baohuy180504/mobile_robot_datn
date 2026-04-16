#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import subprocess
import time

class AutoMapSaver(Node):
    def __init__(self):
        super().__init__('auto_map_saver')
        # Lắng nghe lệnh vận tốc của Nav2
        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10)
        
        self.last_move_time = time.time()
        self.save_timeout = 20.0  # 20 giây không di chuyển = Quét xong
        self.map_saved = False

        # Timer kiểm tra định kỳ mỗi giây
        self.timer = self.create_timer(1.0, self.check_status)
        self.get_logger().info('Đang giám sát quá trình Explore. Sẽ tự động lưu map nếu xe dừng 20s...')

    def cmd_vel_callback(self, msg):
        # Nếu xe đang được lệnh di chuyển (tiến hoặc xoay)
        if abs(msg.linear.x) > 0.01 or abs(msg.angular.z) > 0.01:
            self.last_move_time = time.time()

    def check_status(self):
        if self.map_saved:
            return
            
        elapsed_time = time.time() - self.last_move_time
        
        # Nếu đã quá 20s không nhúc nhích
        if elapsed_time > self.save_timeout:
            self.get_logger().info('Phát hiện xe đã hoàn thành quét không gian! Đang tiến hành lưu bản đồ...')
            self.save_map()
            self.map_saved = True
            # Tự sát Node sau khi lưu xong
            raise SystemExit

    def save_map(self):
        try:
            # Gọi lệnh CLI của nav2_map_server để chụp map
            command = ['ros2', 'run', 'nav2_map_server', 'map_saver_cli', '-f', '/home/huy_ubuntu/test_ros/ros2_ws/src/amr_slam/maps/auto_explored_map']
            subprocess.run(command, check=True)
            self.get_logger().info('✅ ĐÃ LƯU BẢN ĐỒ THÀNH CÔNG tại: amr_slam/maps/auto_explored_map')
        except subprocess.CalledProcessError as e:
            self.get_logger().error(f'❌ Lỗi khi lưu bản đồ: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = AutoMapSaver()
    try:
        rclpy.spin(node)
    except SystemExit:
        rclpy.logging.get_logger("Quitting").info('Hoàn tất nhiệm vụ Auto-Save.')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()