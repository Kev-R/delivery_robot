from setuptools import setup

package_name = 'delivery_control'

setup(
    name=package_name,
    version='0.2.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='delivery_team',
    maintainer_email='you@example.com',
    description='Safety teleop gate node',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'safety_teleop_node = delivery_control.safety_teleop_node:main',
        ],
    },
)
