import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    rtabmap_launch_dir = get_package_share_directory('rtabmap_launch')

    rtabmap_fusion = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(rtabmap_launch_dir, 'launch', 'rtabmap.launch.py')),
        launch_arguments={
            # TỐI ƯU HÓA THEO BÀI BÁO IEEE: Bật chiến lược lai (Lidar ICP + Visual)
            #'rtabmap_args': '--delete_db_on_start --Reg/Force3DoF true --Optimizer/Slam2D true --RGBD/NeighborLinkRefining true --Grid/FromDepth false',
            'rtabmap_args': '--delete_db_on_start --Reg/Strategy 1 --Reg/Force3DoF true --Optimizer/Slam2D true --RGBD/NeighborLinkRefining true --RGBD/ProximityBySpace true --Grid/FromDepth false --Icp/VoxelSize 0.05',
            'frame_id': 'base_footprint',
            
            'visual_odometry': 'false', 
            'odom_topic': '/odom',
            
            # CẬP NHẬT: Topic chuẩn của Camera Astra khi chạy bằng phần cứng thật
            'rgb_topic': '/camera/color/image_raw',
            'depth_topic': '/camera/depth/image_raw',
            'camera_info_topic': '/camera/color/camera_info',
            
            # KÍCH HOẠT LIDAR 2D
            'subscribe_scan': 'true', 
            'scan_topic': '/scan',
            
            'approx_sync': 'true',
            'sync_queue_size': '20',
            'use_sim_time': 'false', # Đã thiết lập chuẩn cho thực tế
            'rviz': 'false', 
            'rtabmap_viz': 'false', 
        }.items()
    )
    return LaunchDescription([rtabmap_fusion])