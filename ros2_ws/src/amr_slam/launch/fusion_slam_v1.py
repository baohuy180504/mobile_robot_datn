import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():

    # ---------------------------------------------------------
    # 1. VISUAL ODOMETRY (Tạo Mắt thần bù sai số cho UKF)
    # ---------------------------------------------------------
    rgbd_odometry_node = Node(
        package='rtabmap_odom',
        executable='rgbd_odometry',
        name='rgbd_odometry',
        output='screen',
        parameters=[{
            'frame_id': 'base_footprint',
            'odom_frame_id': 'odom',
            'publish_tf': False,       # QUAN TRỌNG: Cấm phát TF để nhường quyền cho UKF
            'approx_sync': True,
            'queue_size': 20,
            'wait_for_transform': 0.2,
        }],
        remappings=[
            ('rgb/image', '/camera/color/image_raw'),
            ('depth/image', '/camera/depth/image_raw'),
            ('rgb/camera_info', '/camera/color/camera_info'),
            ('odom', '/camera/odom')   # Bắn odom ảo ra luồng riêng cho UKF tiêu thụ
        ]
    )

    # ---------------------------------------------------------
    # 2. SEMANTIC SLAM (Vẽ map 2D, 3D và Định vị AI)
    # ---------------------------------------------------------
    rtabmap_node = Node(
        package='rtabmap_slam',
        executable='rtabmap',
        name='rtabmap',
        output='screen',
        parameters=[{
            'frame_id': 'base_footprint',
            'subscribe_depth': True,
            'subscribe_scan': True,
            'subscribe_odom_info': True,
            'approx_sync': True,
            'queue_size': 50,
            
            # --- CẤU HÌNH SEMANTIC AI (MỚI) ---
            'RGBD/LandmarkRobust': 'true',  # Cho phép tối ưu hóa tọa độ xe dựa trên Đồ vật (Landmark)
            'Marker/Dictionary': '0',       # Lắng nghe topic AI thay vì quét mã QR truyền thống
            
            # --- CẤU HÌNH VẼ MAP ---
            'Optimizer/Slam2D': 'true',     # Ép vẽ map trên mặt phẳng
            'Grid/FromDepth': 'false',      # Dùng Lidar để vẽ Map 2D (chính xác hơn Camera)
            'Reg/Strategy': '1',            # Dùng Lidar (ICP) để nối Vòng lặp (Giống bài báo IEEE)
        }],
        remappings=[
            ('odom', '/odom'), # Nhận Odom chuẩn đã được lọc từ UKF
            ('scan', '/scan_filtered'),
            ('rgb/image', '/camera/color/image_raw'),
            ('depth/image', '/camera/depth/image_raw'),
            ('rgb/camera_info', '/camera/color/camera_info'),
            
            # Hứng dữ liệu hộp bao Bounding Box từ YOLO
            ('landmarks', '/yolo/detections') 
        ],
        arguments=['--delete_db_on_start']
    )

    # ---------------------------------------------------------
    # 3. MÔ HÌNH YOLOv8 (Nhận diện đồ vật theo thời gian thực)
    # ---------------------------------------------------------
    yolo_node = Node(
        package='yolov8_ros',
        executable='yolov8_node',
        name='yolov8_node',
        parameters=[{
            'model': 'yolov8n.pt', # Jetson sẽ tự dùng TensorRT/CUDA nếu có
            'device': 'cuda:0',
            'threshold': 0.60,     # Chỉ ghim lên bản đồ nếu AI chắc chắn > 60%
        }],
        remappings=[
            ('image_raw', '/camera/color/image_raw')
        ]
    )

    return LaunchDescription([
        rgbd_odometry_node,
        rtabmap_node,
        yolo_node
    ])