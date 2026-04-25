# This directory will hold the saved arena map after Phase 2.
# Files generated:
#   arena.pgm   - occupancy grid as a PGM image
#   arena.yaml  - map metadata (resolution, origin, thresholds)
#
# To save the map (after running mapping_launch.py and driving the arena):
#
#   cd ~/delivery_ws/src/delivery_bringup/maps
#   ros2 run nav2_map_server map_saver_cli -f arena
#
# IMPORTANT: cd into THIS directory first. The map_saver writes the path
# you give it as the literal `image:` field in the yaml, so saving from
# anywhere else produces a yaml with a wrong path.
