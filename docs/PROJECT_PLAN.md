# Delivery Robot — Project Plan

A clean step-by-step plan from "fresh workspace" to "robot autonomously
delivering with A\* + DWB and avoiding obstacles."

## Architectural decisions made up front

We use **maximum Yahboom + Nav2 stock components** to minimize integration
risk and free up time for tuning and demo polish. The only custom piece is
our `safety_teleop_node` — a one-file gate that ensures keyboard override
and emergency stop work at all times.

| Component | Source |
|---|---|
| Hardware drivers (motors, lidar, IMU) | Yahboom (stock) |
| State estimation (EKF) | Yahboom (stock, uses `robot_localization`) |
| SLAM (mapping) | Cartographer (via Yahboom's launch) |
| Localization | AMCL (via Nav2) |
| **Global planner: A\*** | **Nav2 NavfnPlanner with `use_astar: true`** |
| Local planner: DWB | Nav2 (stock) |
| Behavior tree, recovery | Nav2 (stock) |
| ★ Safety/teleop gate | **Custom (`delivery_control` package)** |

Configuration we own:
- `nav2_params.yaml` — A\* enabled, frame names match Yahboom's TF tree
- Saved arena map (Phase 2 output)
- RViz config with QoS pre-fixed for Nav2's transient_local map publisher

## Phases

| Phase | Goal | Time est | Deliverable |
|---|---|---|---|
| **0** | First-time setup | 30 min | Workspace built, dockers run |
| **1** | Hardware sanity | 30 min | Teleop drives the robot |
| **2** | Build the map | 1 hour | `arena.pgm` + `arena.yaml` saved |
| **3** | A\* planning, no driving | 1 hour | Green path appears in RViz on goal click |
| **4** | DWB driving | 2 hours | Robot drives to clicked goals |
| **5** | Tuning + dynamic obstacles | 4 hours | Robot avoids tall objects placed mid-run |
| **6** | Polish + report | 6 hours | Video, write-up, multi-goal demo |

Total realistic timeline: **15–20 hours of focused work** over 5–8 sessions.

---

## Phase 0 — Setup

Follow [SETUP.md](SETUP.md). At the end, you should be able to:
- SSH into the robot with X11 forwarding
- Enter the docker
- Build the workspace cleanly
- See `delivery_bringup` and `delivery_control` in `ros2 pkg list`

### Acceptance check

```bash
ros2 pkg list | grep delivery
# expected:
# delivery_bringup
# delivery_control

ros2 launch delivery_bringup hardware_launch.py --show-args
# should print no errors and show available launch arguments
```

---

## Phase 1 — Hardware sanity

Verify the robot's hardware comes up cleanly and we can drive it manually.

### Run

**Terminal 1** — bring up hardware:
```bash
cd ~/codes/delivery_ws && source install/setup.bash
ros2 launch delivery_bringup hardware_launch.py
```

Expected output: a few `INFO` lines for each driver, ending with the lidar
reporting `SLLidar health status: OK`. No FATAL or repeated errors.

**Terminal 2** — drive with our safety teleop:
```bash
cd ~/codes/delivery_ws && source install/setup.bash
ros2 run delivery_control safety_teleop_node
```

You'll see the banner. Press `i` to drive forward, `,` for back, `j`/`l` for
rotation. The robot should respond smoothly. Press `k` to stop.

### Verify topics

In a third terminal:
```bash
ros2 topic hz /scan        # ~10 Hz
ros2 topic hz /odom        # ~20 Hz
ros2 topic hz /cmd_vel     # 30 Hz (constant — our safety node publishes at fixed rate)
```

### Common issues

- **Robot doesn't move**: check Terminal 2 says `[autonomy=OFF]`, check
  `ros2 topic echo /cmd_vel --once` after pressing a key. If `/cmd_vel`
  shows non-zero values but motors don't respond, the robot might be on
  the charger (some robots disable motors while charging) or the docker
  might have a stale ghost process. Try `docker stop $(docker ps -q)`
  and start over.

- **Stuttery teleop**: if you launch RViz here, you'll cause CPU contention.
  Phase 1 doesn't need RViz. Don't open it.

### Acceptance check

You can drive the robot smoothly forward, back, left, right with the
keyboard for at least 30 seconds without losing connection or stuttering.

---

## Phase 2 — Map the arena (Cartographer SLAM)

### Set up the arena

- Set the arena boundaries with whatever walls you have.
- Place static obstacles (cones, boxes) where they'll live during demos.
- **Note:** the lidar scans at ~15-20 cm above the floor. Short cones may
  produce only a few pixels on the map. Use **TALL** obstacles (>30 cm)
  for the dynamic obstacle phase, or accept that small cones will be
  detected but barely visible.

### Run

**Terminal 1** — hardware + Cartographer:
```bash
cd ~/codes/delivery_ws && source install/setup.bash
ros2 launch delivery_bringup mapping_launch.py
```

Wait until you see `[cartographer_ros]: Added trajectory 0` and `pulsed at
~100% real time` in the log.

**Terminal 2** — drive the robot (use Yahboom's stock teleop here, our
safety teleop isn't necessary while mapping):
```bash
ssh -Y jetson@192.168.1.11
./exec_docker.sh
ros2 run yahboomcar_ctrl yahboom_keyboard
```

### Drive plan (this matters!)

Cartographer's loop closure relies on revisiting places. To get a clean map:
- **Drive slowly** (~0.1 m/s). Hit `z` 4-5 times to drop speed.
- **Hug the perimeter** of the arena. Stay ~0.3 m off the walls.
- **Rotate 360° at each corner** before continuing.
- **Drive the full perimeter twice.**
- **Return to your start position** at the end and rotate one more time.
- Total drive time: **3–5 minutes**.
- **DO NOT open RViz during driving.** RViz over X-forwarding consumes CPU
  that Cartographer needs and you'll get a worse map.

### Save the map

When you're back at the start position, in **Terminal 3**:

```bash
ssh -Y jetson@192.168.1.11
./exec_docker.sh
cd ~/codes/delivery_ws/src/delivery_bringup/maps   # ← important: cd HERE
ros2 run nav2_map_server map_saver_cli -f arena
```

You'll see `Map saved successfully`. Two files are created in the maps
directory: `arena.pgm` and `arena.yaml`.

The `cd` step is critical. The map saver records the path you gave it as
the literal `image:` field in the yaml. By cd'ing into the maps directory
first and using `-f arena`, the yaml records `image: arena.pgm` (filename
only), which is the format Nav2's map_server expects.

### Verify the map

Quickly check the yaml looks right:
```bash
cat arena.yaml
```

Expected:
```yaml
image: arena.pgm
mode: trinary
resolution: 0.05
origin: [-1.06, -1.39, 0]   # values will differ, but format must match
negate: 0
occupied_thresh: 0.65
free_thresh: 0.25
```

### Rebuild so the map gets installed

```bash
cd ~/codes/delivery_ws
colcon build --packages-select delivery_bringup --symlink-install
source install/setup.bash

# Verify it's in install/
ls install/delivery_bringup/share/delivery_bringup/maps/
# expected: arena.pgm  arena.yaml  README.md
```

### Optional but recommended: visualize the saved map

In a docker terminal:
```bash
rviz2
```
Add Map display on `/map` (will be empty since map_server isn't running yet
— but you can verify the file by opening it directly with an image viewer
on your laptop after rsync).

### If the map looks bad

A clean map should be a single closed rectangle (the arena) with crisp
black walls and a few small dark spots (your cones). If you see:

- **Ghost walls** (the same wall drawn twice): drift wasn't corrected.
  Redo with more emphasis on rotating at corners and returning to start.

- **Cartographer FATAL crash** with "Non-sorted data added to queue":
  known issue under CPU load on Jetson. Just relaunch and try again,
  saving faster (don't drive longer than ~5 min).

- **Walls but no interior detail**: the lidar didn't see the cones. They're
  too short or too far from where you drove. Drive closer to them on the
  next attempt.

### Acceptance check

`arena.pgm` and `arena.yaml` exist in both `src/.../maps/` and
`install/.../maps/`. The image (open it on your laptop after rsync) shows
a clean closed rectangle representing your arena.

### Save your work to GitHub

```bash
# On laptop, after pulling the map files via rsync:
cd ~/delivery_robot
git add src/delivery_bringup/maps/arena.pgm src/delivery_bringup/maps/arena.yaml
git commit -m "Phase 2: arena map"
git push
```

---

## Phase 3 — A\* planning (no driving yet)

Verify the global planner works without committing to actually driving the
robot. We'll set an initial pose, click goals in RViz, and watch A\* draw
green paths. The robot stays still.

### Run

**Terminal 1** — full Nav2 stack with our map and A\* enabled:
```bash
cd ~/codes/delivery_ws && source install/setup.bash
ros2 launch delivery_bringup navigation_launch.py
```

You'll see lots of log output. Wait for the line:
```
[lifecycle_manager_navigation]: Managed nodes are active
```

This means Nav2 is fully initialized.

You'll also see warnings like `[amcl]: ACML cannot publish a pose...` —
**that's expected** until you set the initial pose in RViz.

**Terminal 2** — safety teleop (we won't enable autonomy this phase):
```bash
ros2 run delivery_control safety_teleop_node
```

**Terminal 3** — RViz with our pre-configured QoS:
```bash
rviz2 -d $(ros2 pkg prefix delivery_bringup)/share/delivery_bringup/rviz/navigation.rviz
```

The map should appear automatically (we pre-set `Durability Policy:
Transient Local` in the RViz config — this avoids the silent "no map
received" issue).

### Set the initial pose

1. Click **"2D Pose Estimate"** in the RViz toolbar
2. Click on the map at the robot's actual location
3. Drag in the direction the robot is facing
4. Release

Within ~1 second:
- Terminal 1's TF errors stop
- The laser scan (red dots) overlays onto your map's walls
- The AMCL particle cloud appears (red arrows) and is dense around the
  pose you set
- A robot icon shows up

If the laser scan does NOT align with the walls, your initial pose was
off. Click 2D Pose Estimate again with a better guess.

### Verify A\* works

1. Click **"2D Goal Pose"** in the RViz toolbar
2. Click somewhere inside the arena (away from walls)

A **green line** (`/plan` topic) should appear from the robot to your
clicked goal, routing around walls. **That's A\* output.**

The robot **does not move** because Terminal 2's safety teleop is in
manual mode (autonomy off). That's correct for this phase.

### Things to test

- Click goals close, far, behind walls, in narrow passages
- Confirm A\* always finds a path through free space, never through walls
- Click a goal in unreachable space (e.g., outside the arena) — Nav2
  should log `Failed to plan`

### Verify with topic info

```bash
ros2 topic echo /plan --once
ros2 topic info /plan -v
```

### Common issues

- **Map doesn't appear in RViz**: open the rviz file again with the path
  above. If you opened raw `rviz2`, the QoS isn't fixed and you'll see
  the blank-map issue.

- **2D Pose Estimate doesn't take**: check Terminal 1 for AMCL log
  messages. If `amcl` is not in the node list (`ros2 node list`), the
  lifecycle didn't activate.

- **No path drawn after Goal click**: AMCL might not have converged.
  Watch the particle cloud — if it's still spread out, the localization
  isn't confident yet. Drive the robot a bit by hand (use `i` in
  Terminal 2) and the particles should collapse.

### Acceptance check

Click a goal anywhere in the arena. A green path appears within 1 second,
routing around walls. The robot is not moving.

---

## Phase 4 — DWB live driving

Now let the robot actually drive. Keep your finger on `k` (e-stop).

### Pre-flight

- Robot on the floor in the middle of the arena
- A clear path from current pose to your planned goal
- You're ready to hit `k` if anything goes wrong

### Run

Same three terminals as Phase 3 are still running. Just:

1. RViz: click **2D Pose Estimate** at the robot's position
2. RViz: click **2D Goal Pose** somewhere in the arena
3. Green path appears (A\*)
4. **Switch focus to Terminal 2 (safety teleop)**
5. **Press SPACE**

You'll see:
```
[autonomy=ON]  speed=0.20 m/s  turn=1.00 rad/s  j/l=ROTATE
```

The robot should start driving toward the goal.

### Override mechanisms

- Press **any movement key** (`i`, `,`, `j`, `l`, etc.) — instantly
  takes over, robot does what you say
- Press **`k`** — E-STOP, also disables autonomy
- Press **space** — toggle autonomy on/off
- Press **`q`/`z`** — adjust your manual teleop speed

### What success looks like

- Robot computes a path on goal click
- After space press, robot rotates to face the path direction
- Robot drives along the path, swerving slightly if it sees obstacles
  via lidar
- Within ~20 cm of the goal, robot stops (DWB's xy_goal_tolerance)
- Terminal 1 logs `Reached the goal!`

### Common issues and fixes

**Robot bumps a wall**: increase `inflation_radius` in `nav2_params.yaml`
from 0.20 to 0.30. Rebuild and relaunch.

**Robot oscillates near goal (forward-back-forward)**: the `RotateToGoal`
critic weight may be too low. Increase `RotateToGoal.scale` from 32.0 to
48.0. Or tighten `xy_goal_tolerance` from 0.20 to 0.30 (counterintuitively,
larger tolerance = less oscillation because DWB stops earlier).

**Robot refuses to move ("All trajectories collide")**: the lidar might
be seeing the chassis. Increase `laser_min_range` in `nav2_params.yaml`
amcl section from 0.15 to 0.20. Also check `obstacle_min_range` in both
costmap layers.

**Robot drives but path keeps replanning loop**: AMCL is unconfident.
Drive the robot manually for 10 seconds to localize, then try again.

### Acceptance check

Click a 2D Goal Pose anywhere in your arena, press space, robot drives
to the goal and stops. You can do this 3 times in a row without any
manual intervention beyond clicking goals.

---

## Phase 5 — Tuning and dynamic obstacles

This is where you spend the most time and where the project becomes a
"delivery robot" rather than just "a robot that drives to points."

### 5a — DWB tuning

For your final demo, you want consistent, smooth driving. Things to tune:

| Parameter | Effect |
|---|---|
| `inflation_radius` | Larger = stays farther from walls. Try 0.15-0.30. |
| `cost_scaling_factor` | Larger = sharper inflation falloff (less middle-of-corridor preference) |
| `PathDist.scale` | Higher = follows global plan more closely |
| `GoalDist.scale` | Higher = aims more directly at goal (might cut corners) |
| `RotateToGoal.scale` | Higher = faces forward toward goal more aggressively |
| `xy_goal_tolerance` | Larger = stops earlier (avoids oscillation) |
| `sim_time` | Longer = considers more future. Higher CPU cost. |
| `vx_samples`, `vtheta_samples` | More = smoother but more CPU. 20 is fine. |

Edit `src/delivery_bringup/config/nav2_params.yaml`, rebuild, relaunch.

Don't tune everything at once — change one parameter, run 3 trials, decide
if it's better. Document your tuning runs.

### 5b — Dynamic obstacles

The selling feature of having a local planner is reactive obstacle
avoidance — the robot handles obstacles that weren't on the map.

**Important: use TALL obstacles.** Your A1 lidar scans at ~15-20 cm
above the floor. Short objects (rolling balls, books) won't be reliably
detected. Use:
- Cardboard tubes (paper towel rolls work)
- Standing water bottles
- Stacked boxes >25 cm tall
- A textbook on its end

**Test scenarios:**

1. **Static unmapped obstacle**: place a tall obstacle in the planned path
   AFTER the robot starts driving. It should slow, swerve, continue.

2. **Slow-moving obstacle**: roll a tall box across the robot's path at
   walking pace. Robot should stop or swerve.

3. **Sudden obstacle**: place an obstacle directly in front of the robot
   while it's driving. Robot should brake before contact.

### 5c — Logging for the report

For each scenario, record a rosbag:
```bash
ros2 bag record -a -o my_run_1
```

You'll get bag files you can replay later for analysis.

### Acceptance check

The robot completes a 3-meter delivery run while you walk into its path
with a tall object. It does not collide.

---

## Phase 6 — Polish + report

### 6a — Multi-goal delivery (optional but cool)

Write a small script that publishes a sequence of goals (warehouse to
station 1, then to station 2, then back to base). Use the `nav2_simple_commander`
Python API or the action client interface for `/navigate_to_pose`.

Skeleton:
```python
from nav2_simple_commander.robot_navigator import BasicNavigator
from geometry_msgs.msg import PoseStamped

navigator = BasicNavigator()
navigator.waitUntilNav2Active()
goal1 = make_pose(1.0, 0.5, yaw=0.0)
goal2 = make_pose(1.5, -0.5, yaw=1.57)
navigator.goThroughPoses([goal1, goal2])
```

### 6b — Video

Record at least:
- A clean 30-second autonomous delivery run
- A 30-second dynamic obstacle avoidance demo
- Optional: visualization of the planned path in RViz overlaid on the run

### 6c — Report

Structure your report around these sections:

1. **Architecture** — the diagram in the README, plus what's stock vs
   custom and why
2. **SLAM / mapping** — Cartographer choice over gmapping, the carpet
   drift problem, loop closure, your saved map
3. **Localization** — AMCL, particle filter dynamics, initial pose
   sensitivity
4. **Global planning (A\*)** — Nav2's NavfnPlanner, how `use_astar: true`
   changes its behavior, comparison to Dijkstra
5. **Local planning (DWB)** — how DWB samples velocity space and scores
   trajectories, why mecanum strafe is disabled here, your tuning iterations
6. **Safety architecture** — the safety_teleop gate, the cmd_vel remap,
   why this matters for live testing
7. **Results** — quantitative: success rate, avg time-to-goal, deviation
   from planned path. Qualitative: video links.
8. **Limitations** — lidar height, carpet drift, CPU constraints,
   no recovery from kidnapped robot, etc.
9. **Future work** — re-enable mecanum strafe in DWB, add a depth camera
   for low obstacles, multi-robot

---

## When things go wrong

A running list of issues and resolutions for this project:

### "AMCL cannot publish a pose"
You haven't clicked 2D Pose Estimate yet. Click it on the map at the
robot's actual location.

### "No map received" in RViz
QoS mismatch. Use the bundled rviz config:
`rviz2 -d $(ros2 pkg prefix delivery_bringup)/share/delivery_bringup/rviz/navigation.rviz`

### Cartographer FATAL crash
"Non-sorted data added to queue" — happens under CPU load on Jetson Nano.
Just relaunch. Don't run RViz during mapping.

### Map saver "Failed to write map"
The maps directory doesn't exist. `mkdir -p src/delivery_bringup/maps`,
then re-save.

### Map appears in RViz but Nav2 doesn't load it
Check your `arena.yaml` — the `image:` field should be just `arena.pgm`,
not a path. If it has a path, regenerate by `cd`-ing into the maps
directory before running map_saver.

### Robot moves when I press a key but not when autonomy enabled
Check `ros2 topic info /cmd_vel_nav -v`. Should show `controller_server`
as publisher (1) and `safety_teleop` as subscriber (1). If publisher is 0,
the SetRemap in our launch file isn't working — check `navigation_launch.py`.

### Robot drives in circles or generally weirdly
AMCL hasn't converged. Drive manually for 10 seconds first to give it
movement to triangulate from. Then try again.
