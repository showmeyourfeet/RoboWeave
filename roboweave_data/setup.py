from setuptools import find_packages, setup

package_name = "roboweave_data"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["tests"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", [
            "config/data_params.yaml",
        ]),
        ("share/" + package_name + "/launch", ["launch/data.launch.py"]),
    ],
    install_requires=["setuptools", "roboweave-interfaces"],
    zip_safe=True,
    maintainer="RoboWeave",
    maintainer_email="roboweave@example.com",
    description="Passive data recording and episode management for RoboWeave",
    license="MIT",
    entry_points={
        "console_scripts": [
            "data_node = roboweave_data.data_node:main",
        ],
    },
)
