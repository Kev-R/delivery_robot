cmake_minimum_required(VERSION 3.5)
project(delivery_bringup)

find_package(ament_cmake REQUIRED)

# Install everything that needs to be available at runtime under
# install/delivery_bringup/share/delivery_bringup/...
install(
  DIRECTORY launch config maps rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
