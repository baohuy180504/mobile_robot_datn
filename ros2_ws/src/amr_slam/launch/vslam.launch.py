import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    rtabmap_launch_dir = get_package_share_directory('rtabmap_launch')

    rtabmap = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(rtabmap_launch_dir, 'launch', 'rtabmap.launch.py')),
        launch_arguments={
            # KHÓA CHẶT 2D VÀ TỰ TIN GHÉP MAP (Vì đã có vật thể hỗ trợ)
            #'rtabmap_args': '--delete_db_on_start --Reg/Force3DoF true --Optimizer/Slam2D true',
            'rtabmap_args': '--delete_db_on_start --Reg/Force3DoF true --Optimizer/Slam2D true --RGBD/ProximityBySpace true --RGBD/LinearUpdate 0.05 --RGBD/AngularUpdate 0.05',
            'frame_id': 'base_footprint',
            
            # TRẢ LẠI QUYỀN ĐO ĐƯỜNG CHO BÁNH XE
            'visual_odometry': 'false', 
            'odom_topic': '/odom',
            
            'rgb_topic': '/camera/color/image_raw',
            'depth_topic': '/camera/depth/image_raw',
            'camera_info_topic': '/camera/color/camera_info',
            'qos': '2',
            
            'subscribe_scan': 'false', # Giữ nguyên tắt Lidar
            
            'approx_sync': 'true',
            'sync_queue_size': '20',
            'topic_queue_size': '20',
            
            'use_sim_time': 'false',
            'rviz': 'false', 
            'rtabmap_viz': 'false', 
        }.items()
    )

    return LaunchDescription([rtabmap])