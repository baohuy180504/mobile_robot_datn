"""
fusion_slam.launch.py — package: amr_slam

Bản sửa lỗi use_merged_scan:
- Dùng OpaqueFunction để đọc trực tiếp giá trị launch argument tại runtime.
- Khi use_merged_scan:=true, slam_toolbox chắc chắn nhận scan_topic=/scan_merged.
- Khi use_merged_scan:=false, slam_toolbox nhận scan_topic=/scan_filtered.
"""

import os
import math

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def launch_setup(context, *args, **kwargs):
    amr_slam_pkg = get_package_share_directory("amr_slam")
    mapper_config = os.path.join(
        amr_slam_pkg,
        "config",
        "mapper_params_fusion.yaml"
    )

    use_merged_scan = _as_bool(LaunchConfiguration("use_merged_scan").perform(context))
    enable_octomap = _as_bool(LaunchConfiguration("enable_octomap").perform(context))
    octomap_frame = LaunchConfiguration("octomap_frame").perform(context)
    octo_resolution = LaunchConfiguration("octo_resolution").perform(context)

    slam_scan_topic = "/scan_merged" if use_merged_scan else "/scan_filtered"

    nodes = []

    nodes.append(
        LogInfo(msg=[
            "\n",
            "╔════════════════════════════════════════════════════════════╗\n",
            "║ FUSION SLAM — selected runtime configuration              ║\n",
            "╠════════════════════════════════════════════════════════════╣\n",
            f"║ slam_toolbox scan_topic : {slam_scan_topic:<27} ║\n",
            f"║ OctoMap enabled         : {str(enable_octomap):<27} ║\n",
            f"║ OctoMap frame           : {octomap_frame:<27} ║\n",
            "╚════════════════════════════════════════════════════════════╝\n",
        ])
    )

    # 1) Depth PointCloud -> virtual LaserScan
    nodes.append(
        Node(
            package="pointcloud_to_laserscan",
            executable="pointcloud_to_laserscan_node",
            name="depth_to_laserscan",
            output="screen",
            remappings=[
                ("cloud_in", "/camera/depth/points"),
                ("scan", "/scan_camera"),
            ],
            parameters=[{
                "target_frame": "laser_frame",
                "transform_tolerance": 0.20,

                # Chỉ lấy vật cản cao hơn mặt phẳng LiDAR, tránh sàn.
                "min_height": 0.05,
                "max_height": 1.20,

                # Astra Mini S/Pro FOV ngang khoảng 58–60 độ.
                "angle_min": -0.55,
                "angle_max": 0.55,
                "angle_increment": 0.00873,

                "range_min": 0.60,
                "range_max": 4.50,

                "scan_time": 0.067,
                "use_inf": True,
                "inf_epsilon": 1.0,
                "concurrency_level": 1,
                "use_sim_time": False,
            }]
        )
    )

    # 2) Merge LiDAR filtered scan + virtual camera scan
    nodes.append(
        Node(
            package="amr_slam",
            executable="scan_merger.py",
            name="scan_merger",
            output="screen",
            parameters=[{
                "lidar_topic": "/scan_filtered",
                "camera_topic": "/scan_camera",
                "output_topic": "/scan_merged",
                "output_frame": "laser_frame",
                "angle_min": -math.pi,
                "angle_max": math.pi,
                "angle_increment": 0.00436,
                "range_min": 0.10,
                "range_max": 11.0,
                "camera_timeout": 1.0,

                # Giai đoạn an toàn: LiDAR là chính, camera chỉ bù chỗ LiDAR không có beam hợp lệ.
                # Khi mọi thứ sạch mới thử đổi thành "nearest".
                "merge_mode": "fill_gaps_only",
            }]
        )
    )

    # 3) SLAM Toolbox — chọn scan_topic theo use_merged_scan tại runtime
    nodes.append(
        Node(
            package="slam_toolbox",
            executable="async_slam_toolbox_node",
            name="slam_toolbox",
            output="screen",
            parameters=[
                mapper_config,
                {
                    "use_sim_time": False,
                    "scan_topic": slam_scan_topic,
                }
            ]
        )
    )

    # 4) OctoMap 3D
    if enable_octomap:
        nodes.append(
            Node(
                package="octomap_server",
                executable="octomap_server_node",
                name="octomap_server",
                output="screen",
                remappings=[
                    ("cloud_in", "/camera/depth/points"),
                    ("projected_map", "/map3d"),
                ],
                parameters=[{
                    "use_sim_time": False,
                    "frame_id": octomap_frame,
                    "base_frame_id": "base_footprint",
                    "resolution": float(octo_resolution),

                    "pointcloud_min_z": 0.05,
                    "pointcloud_max_z": 2.00,
                    "occupancy_min_z": 0.05,
                    "occupancy_max_z": 2.00,

                    # Tên tham số dạng dấu chấm phù hợp octomap_server ROS2.
                    "sensor_model.max_range": 4.50,
                    "sensor_model.hit": 0.70,
                    "sensor_model.miss": 0.40,
                    "sensor_model.min": 0.12,
                    "sensor_model.max": 0.97,

                    "compress_map": True,
                    "filter_ground": True,
                    "ground_filter.distance": 0.04,
                    "ground_filter.angle": 0.15,
                    "ground_filter.plane_distance": 0.07,
                }]
            )
        )

    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            "use_merged_scan",
            default_value="false",
            description="true: slam_toolbox dùng /scan_merged; false: dùng /scan_filtered"
        ),
        DeclareLaunchArgument(
            "enable_octomap",
            default_value="true",
            description="Bật/tắt OctoMap 3D"
        ),
        DeclareLaunchArgument(
            "octomap_frame",
            default_value="odom",
            description="Frame tích lũy OctoMap. Debug nên dùng odom; khi ổn có thể đổi map."
        ),
        DeclareLaunchArgument(
            "octo_resolution",
            default_value="0.05",
            description="Độ phân giải voxel OctoMap"
        ),
        OpaqueFunction(function=launch_setup),
    ])
