#!/usr/bin/env python3

import rclpy
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from geometry_msgs.msg import PoseStamped
import time

def main():
    rclpy.init()
    nav = BasicNavigator()

    # 1. Chờ Nav2 sẵn sàng
    nav.waitUntilNav2Active()

    # 2. KHAI BÁO CÁC ĐIỂM DỪNG
    goal_poses = []

    # ĐIỂM 1: Thay vì đợi 2D Pose, Huy hãy lấy tọa độ lúc bạn vừa đặt Pose Estimate 
    # (Ví dụ mình lấy tọa độ điểm 1 ban đầu của bạn hoặc tọa độ 0,0)
    ph = PoseStamped()
    ph.header.frame_id = 'map'
    ph.pose.position.x = 0.0  # Chỉnh lại số này theo vị trí bạn thường đặt Pose Estimate
    ph.pose.position.y = 0.0
    ph.pose.orientation.w = 1.0

    # ĐIỂM 2
    p1 = PoseStamped()
    p1.header.frame_id = 'map'
    p1.pose.position.x = 3.088
    p1.pose.position.y = 0.747
    p1.pose.orientation.z = 0.694
    p1.pose.orientation.w = 0.720

    # ĐIỂM 3
    p2 = PoseStamped()
    p2.header.frame_id = 'map'
    p2.pose.position.x = -4.862
    p2.pose.position.y = -1.385
    p2.pose.orientation.z = 0.017
    p2.pose.orientation.w = 1.000

    # ĐIỂM 4
    p3 = PoseStamped()
    p3.header.frame_id = 'map'
    p3.pose.position.x = -3.204
    p3.pose.position.y = 3.453 
    p3.pose.orientation.z = 1.000
    p3.pose.orientation.w = -0.020

    # Thêm vào danh sách theo thứ tự
    goal_poses.append(p1)
    goal_poses.append(p2)
    goal_poses.append(p3)
    goal_poses.append(ph) # Quay về điểm 1

    print("Hệ thống đã sẵn sàng. Đang gửi danh sách Waypoints...")

    # 3. THỰC THI
    nav.followWaypoints(goal_poses)

    while not nav.isTaskComplete():
        feedback = nav.getFeedback()
        if feedback:
            print(f'Đang đi đến trạm số: {feedback.current_waypoint + 1}')

    print(f"Hoàn thành! Kết quả: {nav.getResult()}")
    rclpy.shutdown()

if __name__ == '__main__':
    main()