# Setup — first time on the robot

This is the one-time setup needed to get this workspace running on the
Yahboom ROSMASTER X3.

## On your laptop

You need WSL with `ssh` and `rsync`. To enable X11 forwarding for RViz:

```bash
# Inside WSL ~/.bashrc:
export LIBGL_ALWAYS_INDIRECT=1
export QT_X11_NO_MITSHM=1
```

Then `source ~/.bashrc`. Test with `xclock` (after starting the robot's Docker
and SSH'ing with `-Y`, you'll be able to see RViz windows).

## Push the workspace to the robot

From a WSL terminal on your laptop:

```bash
# After cloning this repo to your laptop (e.g. ~/delivery_robot)
rsync -avz --modify-window=2 \
    --exclude='build/' --exclude='install/' --exclude='log/' \
    --exclude='__pycache__/' --exclude='*.pyc' --exclude='.git/' \
    ~/delivery_robot/ \
    jetson@192.168.1.11:/home/jetson/codes/delivery_ws/
```

Password: `yahboom`. Replace `192.168.1.11` with the IP shown on the robot's
OLED screen if different.

## On the robot — first time

```bash
ssh -Y jetson@192.168.1.11
./run_docker.sh

# Inside the docker:
cd ~/codes/delivery_ws
colcon build --symlink-install
source install/setup.bash
```

`colcon build` will compile `delivery_bringup` (just file installation —
no compilation needed) and `delivery_control` (the safety teleop Python
package). Should take <30 seconds.

If you see warnings about missing dependencies (`yahboomcar_nav`, `nav2_bringup`,
etc.), those are fine — `colcon build` checks dependencies at build time but
they're already installed in the docker image.

## Subsequent sessions

```bash
ssh -Y jetson@192.168.1.11
./run_docker.sh
cd ~/codes/delivery_ws
source install/setup.bash
# now ready to launch any phase
```

Open additional terminals into the same docker with:
```bash
ssh -Y jetson@192.168.1.11
./exec_docker.sh
cd ~/codes/delivery_ws
source install/setup.bash
```

## Editing on laptop, deploying to robot

The recommended workflow is to edit on your laptop and rsync to the robot.
Run this command from your laptop after edits:

```bash
rsync -avz --modify-window=2 \
    --exclude='build/' --exclude='install/' --exclude='log/' \
    --exclude='__pycache__/' --exclude='*.pyc' --exclude='.git/' \
    ~/delivery_robot/ \
    jetson@192.168.1.11:/home/jetson/codes/delivery_ws/
```

After rsync, on the robot, rebuild only what changed:

```bash
cd ~/codes/delivery_ws
colcon build --packages-select delivery_bringup --symlink-install
# or:
colcon build --packages-select delivery_control --symlink-install
source install/setup.bash
```

## Pulling the map back to your laptop

After Phase 2 (mapping), you'll have `arena.pgm` and `arena.yaml` on the robot.
Pull them to your laptop and commit them:

```bash
# On your laptop
rsync -avz --modify-window=2 \
    jetson@192.168.1.11:/home/jetson/codes/delivery_ws/src/delivery_bringup/maps/ \
    ~/delivery_robot/src/delivery_bringup/maps/

cd ~/delivery_robot
git add src/delivery_bringup/maps/arena.{pgm,yaml}
git commit -m "Phase 2: saved arena map"
git push
```
