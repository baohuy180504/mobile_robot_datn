import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    rtabmap_launch_dir = get_package_share_directory('rtabmap_launch')
    db_path = os.path.expanduser('~/test_ros/ros2_ws/src/amr_slam/maps/my_3d_map.db')

    rtabmap = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(rtabmap_launch_dir, 'launch', 'rtabmap.launch.py')),
        launch_arguments={
            'rtabmap_args': '--Reg/Force3DoF true --Optimizer/Slam2D true --Grid/FromDepth true --publish_tf true',
            #'rtabmap_args': '--Reg/Force3DoF true --Optimizer/Slam2D true --Grid/FromDepth true --publish_tf true --Vis/MinInliers 30 --RGBD/OptimizeMaxError 0.1',
            'localization': 'true',
            'database_path': db_path,
            
            'frame_id': 'base_footprint',
            'visual_odometry': 'false', 
            'odom_topic': '/odom',
            
            'rgb_topic': '/camera/astra/image_raw',
            'depth_topic': '/camera/astra/depth/image_raw',
            'camera_info_topic': '/camera/astra/camera_info',
            'qos': '2',
            
    
            #'subscribe_scan': 'true', 
            'subscribe_scan': 'false',
            'scan_topic': '/scan',
            
            'approx_sync': 'true',
            'sync_queue_size': '20',
            
            'use_sim_time': 'false',
            'rviz': 'false', 
            'rtabmap_viz': 'false', 
        }.items()
    )

    return LaunchDescription([rtabmap])