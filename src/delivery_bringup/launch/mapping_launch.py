"""
mapping_launch.py
-----------------
Phase 2: build a map of the arena using Cartographer SLAM.

What this starts:
  - Yahboom hardware (via hardware_launch.py)
  - Cartographer SLAM (via Yahboom's map_cartographer_launch.py)

Usage:
  # Terminal 1:
  ros2 launch delivery_bringup mapping_launch.py

  # Terminal 2 (drive the robot):
  ros2 run yahboomcar_ctrl yahboom_keyboard

  # Drive deliberately:
  #   - slow speed (~0.1 m/s)
  #   - hug perimeter for two laps
  #   - rotate 360 at corners for loop closure
  #   - return to start position
  # DO NOT open RViz during driving (CPU saturation)

  # When done, in Terminal 3:
  cd ~/delivery_ws/src/delivery_bringup/maps
  ros2 run nav2_map_server map_saver_cli -f arena

  # IMPORTANT: cd into the maps directory FIRST so the YAML's image
  # field is just "arena.pgm" (filename only, not a path).

  # Then rebuild so the map is installed for Phase 3:
  cd ~/delivery_ws
  colcon build --packages-select delivery_bringup --symlink-install
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    delivery_share = get_package_share_directory('delivery_bringup')
    yahboomcar_nav_share = get_package_share_directory('yahboomcar_nav')

    # 1. Hardware
    hardware = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(delivery_share, 'launch', 'hardware_launch.py')
        ),
    )

    # 2. Cartographer SLAM (Yahboom's launch).
    # We chose Cartographer over gmapping because it has better loop closure,
    # producing cleaner maps on carpet where wheel slip causes drift.
    cartographer = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(yahboomcar_nav_share, 'launch', 'map_cartographer_launch.py')
        ),
    )

    return LaunchDescription([hardware, cartographer])
