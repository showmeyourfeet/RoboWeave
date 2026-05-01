from setuptools import find_packages, setup

package_name = "roboweave_control"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["tests"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", [
            "config/control_params.yaml",
            "config/sim_arm.yaml",
            "config/sim_gripper.yaml",
        ]),
        ("share/" + package_name + "/launch", ["launch/control.launch.py"]),
    ],
    install_requires=["setuptools", "roboweave-interfaces"],
    zip_safe=True,
    maintainer="RoboWeave",
    maintainer_email="roboweave@example.com",
    description="Hardware abstraction and control execution for RoboWeave",
    license="MIT",
    entry_points={
        "console_scripts": [
            "control_node = roboweave_control.control_node:main",
        ],
    },
)
