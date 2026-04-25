"""
hardware_launch.py
------------------
Phase 1: bring up the robot hardware only. No SLAM, no Nav2.

What this starts:
  - All Yahboom hardware nodes via their stock laser_bringup_launch.py
    (driver, lidar, EKF, IMU filter, joystick, TFs)

This is the foundation that every other phase depends on.

Usage:
  ros2 launch delivery_bringup hardware_launch.py

Verify:
  ros2 topic list  # should show /scan, /odom, /imu, /tf, etc.
  ros2 topic hz /scan  # ~10 Hz from the lidar
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    yahboomcar_nav_share = get_package_share_directory('yahboomcar_nav')

    # Yahboom's laser_bringup_launch.py launches the FULL stack:
    #   - Mcnamu_driver_X3 (motor controller)
    #   - sllidar_node (lidar)
    #   - imu_filter_madgwick (IMU filtering)
    #   - ekf_node (wheel + IMU sensor fusion)
    #   - robot_state_publisher (URDF + TFs)
    #   - yahboom_joy_X3 (gamepad if connected)
    #   - static_transform_publisher (base_link <-> laser)
    #
    # Despite the name "laser_bringup", this is the everything-but-nav2 launch.
    hardware = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(yahboomcar_nav_share, 'launch', 'laser_bringup_launch.py')
        ),
    )

    return LaunchDescription([hardware])
