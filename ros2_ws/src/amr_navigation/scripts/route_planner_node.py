#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import json
import os
import math
import time
from geometry_msgs.msg import PoseStamped
from visualization_msgs.msg import Marker, MarkerArray
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

class RoutePlannerNode(Node):
    def __init__(self):
        super().__init__('route_planner_node')
        
        # Publisher để hiển thị lộ trình trên RViz2
        self.marker_pub = self.create_publisher(MarkerArray, '/route_markers', 10)
        
        # Khởi tạo bộ điều khiển Nav2
        self.navigator = BasicNavigator()

        # Cập nhật đường dẫn tuyệt đối tới file json (Đảm bảo file nằm đúng đây)
        self.route_file = os.path.join(os.getcwd(), 'src', 'amr_navigation', 'scripts', 'route_data.json') 

        self.waypoints_ros = []
        self.load_route_from_json()

    def yaw_to_quaternion(self, yaw):
        """Công thức toán học chuyển đổi góc Yaw (Radian) sang Quaternion cho không gian 2D"""
        qx = 0.0
        qy = 0.0
        qz = math.sin(yaw / 2.0)
        qw = math.cos(yaw / 2.0)
        return qx, qy, qz, qw

    def load_route_from_json(self):
        """Đọc file JSON và chuyển đổi sang danh sách PoseStamped"""
        # Sửa lại tìm kiếm đường dẫn dự phòng nếu chạy ở thư mục khác
        if not os.path.exists(self.route_file):
            fallback_path = os.path.join(os.getcwd(), 'route_data.json')
            if os.path.exists(fallback_path):
                self.route_file = fallback_path
            else:
                self.get_logger().error(f"Không tìm thấy file lộ trình tại: {self.route_file}")
                return

        try:
            with open(self.route_file, 'r') as f:
                data = json.load(f)
                
            for pt in data:
                pose = PoseStamped()
                pose.header.frame_id = 'map'
                pose.header.stamp = self.get_clock().now().to_msg()
                pose.pose.position.x = pt['x']
                pose.pose.position.y = pt['y']
                pose.pose.position.z = 0.0
                
                # Áp dụng hàm tính toán nội bộ thay vì dùng thư viện tf_transformations
                qx, qy, qz, qw = self.yaw_to_quaternion(pt['yaw'])
                pose.pose.orientation.x = qx
                pose.pose.orientation.y = qy
                pose.pose.orientation.z = qz
                pose.pose.orientation.w = qw
                
                self.waypoints_ros.append(pose)
                
            self.get_logger().info(f"Đã nạp thành công {len(self.waypoints_ros)} điểm từ JSON.")
        except Exception as e:
            self.get_logger().error(f"Lỗi khi đọc file JSON: {str(e)}")

    def publish_markers(self):
        """Vẽ lộ trình lên RViz2 với kích thước nhỏ gọn"""
        marker_array = MarkerArray()
        now = self.get_clock().now().to_msg()

        # 1. Vẽ đường nối màu xanh (Line Strip)
        line_marker = Marker()
        line_marker.header.frame_id = "map"
        line_marker.header.stamp = now
        line_marker.ns = "route"
        line_marker.id = 0
        line_marker.type = Marker.LINE_STRIP
        line_marker.action = Marker.ADD
        line_marker.scale.x = 0.03 # Độ dày đường line mảnh
        line_marker.color.r, line_marker.color.g, line_marker.color.b, line_marker.color.a = 0.0, 0.6, 1.0, 0.8
        
        for wp in self.waypoints_ros:
            line_marker.points.append(wp.pose.position)
        marker_array.markers.append(line_marker)

        # 2. Vẽ điểm và mũi tên hướng (Màu đỏ)
        for i, wp in enumerate(self.waypoints_ros):
            # Mũi tên hướng (ARROW)
            arrow = Marker()
            arrow.header.frame_id = "map"
            arrow.header.stamp = now
            arrow.ns = "waypoints"
            arrow.id = i + 1
            arrow.type = Marker.ARROW
            arrow.pose = wp.pose
            arrow.scale.x = 0.15
            arrow.scale.y = 0.025
            arrow.scale.z = 0.025
            arrow.color.r, arrow.color.g, arrow.color.b, arrow.color.a = 1.0, 0.0, 0.0, 1.0
            marker_array.markers.append(arrow)

            # Chữ P1, P2...
            text = Marker()
            text.header.frame_id = "map"
            text.header.stamp = now
            text.ns = "labels"
            text.id = i + 100
            text.type = Marker.TEXT_VIEW_FACING
            text.text = f"P{i+1}"
            text.pose.position.x = wp.pose.position.x
            text.pose.position.y = wp.pose.position.y
            text.pose.position.z = 0.15
            text.scale.z = 0.1
            text.color.r, text.color.g, text.color.b, text.color.a = 1.0, 1.0, 1.0, 1.0
            marker_array.markers.append(text)

        self.marker_pub.publish(marker_array)

    def run(self):
        self.navigator.waitUntilNav2Active()
        self.publish_markers()

        if not self.waypoints_ros:
            self.get_logger().error("Không có dữ liệu lộ trình để chạy!")
            return

        self.get_logger().info("Bắt đầu thực hiện lộ trình theo từng chặng...")
        
        # Lặp qua từng điểm và yêu cầu Nav2 đi tới điểm đó
        for i, wp in enumerate(self.waypoints_ros):
            self.get_logger().info(f"==> Đang tiến tới điểm P{i+1}...")
            
            # Sử dụng goToPose thay vì goThroughPoses
            self.navigator.goToPose(wp)

            count = 0
            while not self.navigator.isTaskComplete():
                count += 1
                feedback = self.navigator.getFeedback()
                if feedback and count % 10 == 0:
                    self.get_logger().info(f"P{i+1}: Còn lại {feedback.distance_remaining:.2f} m")
                
                # Cập nhật marker để RViz2 không bị mất hình
                if count % 20 == 0:
                    self.publish_markers()

            result = self.navigator.getResult()
            if result == TaskResult.SUCCEEDED:
                self.get_logger().info(f" [Thành công] Đã đến P{i+1}!")
                #time.sleep(0.5)
            elif result == TaskResult.CANCELED:
                self.get_logger().warn(f" [Hủy] Lộ trình tới P{i+1} bị hủy.")
                break # Dừng lộ trình nếu bị hủy
            elif result == TaskResult.FAILED:
                self.get_logger().error(f" [Thất bại] Không thể đến P{i+1}. Dừng lộ trình!")
                break # Dừng lộ trình nếu thất bại

        self.get_logger().info('Đã hoàn tất toàn bộ tiến trình!')

def main():
    rclpy.init()
    node = RoutePlannerNode()
    node.run()
    rclpy.shutdown()

if __name__ == '__main__':
    main()