from setuptools import find_packages, setup

package_name = "roboweave_planning"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["tests"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", [
            "config/planning_params.yaml",
            "config/planning_backends.yaml",
        ]),
        ("share/" + package_name + "/launch", ["launch/planning.launch.py"]),
    ],
    install_requires=["setuptools", "roboweave-interfaces", "numpy"],
    zip_safe=True,
    maintainer="RoboWeave",
    maintainer_email="roboweave@example.com",
    description="Planning layer for RoboWeave",
    license="MIT",
    entry_points={
        "console_scripts": [
            "planning_node = roboweave_planning.planning_node:main",
        ],
    },
)
