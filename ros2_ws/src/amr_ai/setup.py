from setuptools import setup, find_packages
from glob import glob
import os

package_name = 'amr_ai'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name,
            ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
        (os.path.join('share', package_name, 'models'),
            glob('models/*')),
        (os.path.join('share', package_name, 'trackers'),
            glob('trackers/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='huyjetson',
    maintainer_email='huyjetson@example.com',
    description='AI package for AMR: person following, fall detection, fire and smoke warning.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # Sẽ thêm sau khi node đã có main()
            'ai_mode_manager = amr_ai.core.ai_mode_manager_node:main',
            'ai_image_probe = amr_ai.core.image_probe_node:main',
            'ai_detector = amr_ai.detectors.ai_detector_node:main',
            'person_tracker = amr_ai.tracking.person_tracker_node:main',
            'follow_goal = amr_ai.nav2.follow_goal_node:main',
            'follow_servo = amr_ai.nav2.follow_servo_node:main',
            'cmd_vel_safety_mux = amr_ai.safety.cmd_vel_safety_mux_node:main',
            'operator_gui = amr_ai.gui.operator_gui_node:main',

        ],
    },
)