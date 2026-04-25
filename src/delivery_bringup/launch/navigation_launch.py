"""
navigation_launch.py
--------------------
Phase 3: full autonomous navigation with A* + DWB.

What this starts:
  - Yahboom hardware (via hardware_launch.py)
  - Nav2 bringup (map_server, AMCL, planner_server, controller_server,
    bt_navigator, recoveries_server, lifecycle_managers)

Architecture:
    [planner_server]      -> /plan         (A* path, NavfnPlanner with use_astar=true)
    [controller_server]   -> /cmd_vel_nav  (DWB local planner, REMAPPED from /cmd_vel)
                                |
                                v
            [safety_teleop_node] (separate terminal)
                                |
                                v /cmd_vel
                       [Yahboom motor driver]

The /cmd_vel remapping is critical: it ensures our safety_teleop_node remains
the ONLY publisher to /cmd_vel. Press space in safety_teleop to enable autonomy,
press 'k' for emergency stop, or any movement key to override.

Usage:
  # Terminal 1:
  ros2 launch delivery_bringup navigation_launch.py

  # Terminal 2 (safety gate):
  ros2 run delivery_control safety_teleop_node

  # Terminal 3 (RViz):
  rviz2 -d $(ros2 pkg prefix delivery_bringup)/share/delivery_bringup/rviz/navigation.rviz

In RViz:
  1. Click "2D Pose Estimate", then click+drag at the robot's actual location
     (this initializes AMCL — until you do this, the planner will spam TF errors)
  2. Click "2D Goal Pose", then click somewhere in the arena
  3. A green path appears (= A* output). The robot won't move yet.
  4. Switch focus to Terminal 2 (safety_teleop), press space to enable autonomy
  5. Robot drives. Press k for e-stop, any movement key to override.
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription,
    DeclareLaunchArgument,
    GroupAction,
)
from launch_ros.actions import SetRemap
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    delivery_share = get_package_share_directory('delivery_bringup')
    nav2_bringup_share = get_package_share_directory('nav2_bringup')

    default_map = os.path.join(delivery_share, 'maps', 'arena.yaml')
    default_params = os.path.join(delivery_share, 'config', 'nav2_params.yaml')

    map_arg = DeclareLaunchArgument(
        'map', default_value=default_map,
        description='Full path to map yaml'
    )
    params_arg = DeclareLaunchArgument(
        'params_file', default_value=default_params,
        description='Full path to Nav2 params yaml'
    )

    # 1. Hardware
    hardware = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(delivery_share, 'launch', 'hardware_launch.py')
        ),
    )

    # 2. Nav2 bringup with /cmd_vel remapped to /cmd_vel_nav
    # SetRemap inside a GroupAction applies to all nodes in the included launch.
    # This is the ONLY clean way to remap topics inside an IncludeLaunchDescription.
    nav2 = GroupAction([
        SetRemap(src='/cmd_vel', dst='/cmd_vel_nav'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_bringup_share, 'launch', 'bringup_launch.py')
            ),
            launch_arguments={
                'map': LaunchConfiguration('map'),
                'use_sim_time': 'false',
                'params_file': LaunchConfiguration('params_file'),
                'autostart': 'true',
            }.items(),
        ),
    ])

    return LaunchDescription([
        map_arg,
        params_arg,
        hardware,
        nav2,
    ])
