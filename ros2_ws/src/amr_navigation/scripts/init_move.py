#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
import time

def main(args=None):
    rclpy.init(args=args)
    node = rclpy.create_node('auto_goal_sender')
    
    # Tạo kênh gửi mục tiêu vào Nav2
    pub = node.create_publisher(PoseStamped, '/goal_pose', 10)
    node.get_logger().info('Đang giả lập click 2D Goal Pose...')
    
    # BÍ QUYẾT SIM-TO-REAL: Chờ cho đến khi Nav2 thực sự kết nối vào topic này
    wait_count = 0
    while pub.get_subscription_count() == 0:
        if wait_count % 2 == 0:
            node.get_logger().info('Đang chờ hệ thống Nav2 mở cửa nhận lệnh...')
        time.sleep(0.5)
        wait_count += 1
        # Chờ tối đa 10 giây (20 vòng) để tránh bị kẹt vô hạn
        if wait_count > 20:
            node.get_logger().error('Không tìm thấy Nav2! Hủy bỏ lệnh khởi động.')
            node.destroy_node()
            rclpy.shutdown()
            return
            
    node.get_logger().info('Đã kết nối với Nav2! Chuẩn bị gửi tọa độ...')
    time.sleep(0.5) # Nghỉ thêm nửa giây cho mạng nội bộ ổn định hẳn
    
    # Tạo tọa độ đích đến (Cách điểm xuất phát 0.5 mét)
    msg = PoseStamped()
    msg.header.frame_id = 'map'
    
    # GỬI NHIỀU LẦN: Đề phòng nhiễu mạng làm rớt gói tin đầu tiên
    for _ in range(3):
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.pose.position.x = 0.5
        msg.pose.position.y = 0.0
        msg.pose.orientation.w = 1.0 # Quay mặt thẳng về phía trước
        pub.publish(msg)
        time.sleep(0.2)
        
    node.get_logger().info('Đã click thành công 0.5m phía trước! Kích hoạt Nav2...')
    
    # Xong việc thì tự hủy
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()