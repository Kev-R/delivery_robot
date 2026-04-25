# Delivery Robot — Yahboom ROSMASTER X3

Autonomous delivery robot using A\* global planning and DWB local planning,
deployed on a Yahboom ROSMASTER X3 (Jetson Nano + A1 lidar) running ROS 2 Foxy.

## Architecture

```
                  ┌─────────────────────────────────────┐
                  │  YAHBOOM HARDWARE STACK             │
                  │  - Mcnamu_driver_X3 (motors)        │
                  │  - sllidar_node (lidar)             │
                  │  - ekf_node (sensor fusion)         │
                  │  - robot_state_publisher (TFs)      │
                  └─────────────────────────────────────┘
                              │   /scan, /odom, /tf
                              ▼
                  ┌─────────────────────────────────────┐
                  │  NAV2 STACK (stock, with our params)│
                  │  - map_server (loads our arena.yaml)│
                  │  - amcl (localization)              │
                  │  - planner_server  → A* path        │
                  │  - controller_server → DWB output   │
                  │  - bt_navigator                     │
                  └─────────────────────────────────────┘
                              │   /cmd_vel_nav (REMAPPED from /cmd_vel)
                              ▼
                  ┌─────────────────────────────────────┐
                  │  ★ safety_teleop_node (custom) ★    │
                  │  Gates Nav2 output by user input.   │
                  │  ONLY publisher to /cmd_vel.        │
                  └─────────────────────────────────────┘
                              │   /cmd_vel
                              ▼
                  ┌─────────────────────────────────────┐
                  │  Robot motors                       │
                  └─────────────────────────────────────┘
```

## Custom code

We rely on Yahboom's hardware drivers and Nav2's planning algorithms.
The only custom node is:

- **safety_teleop_node** (`delivery_control` package) — keyboard teleop
  combined with an autonomy gate. Provides space-toggle autonomy enable,
  per-key teleop override, and `k` for emergency stop.

Everything else is configuration (launch files, Nav2 params, RViz config,
saved map).

## Quick start (after Phase 2 is done)

```bash
# Terminal 1
ros2 launch delivery_bringup navigation_launch.py

# Terminal 2
ros2 run delivery_control safety_teleop_node

# Terminal 3
rviz2 -d $(ros2 pkg prefix delivery_bringup)/share/delivery_bringup/rviz/navigation.rviz
```

In RViz: 2D Pose Estimate (click+drag at robot's location), then 2D Goal Pose
(click target), then in Terminal 2 press space.

## Phase plan

See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for the full step-by-step.

## Setup

See [docs/SETUP.md](docs/SETUP.md) for first-time install on the robot.
