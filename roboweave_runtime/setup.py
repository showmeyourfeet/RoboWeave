from setuptools import find_packages, setup

package_name = "roboweave_runtime"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["tests"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", ["config/runtime_params.yaml"]),
        ("share/" + package_name + "/launch", ["launch/runtime.launch.py"]),
    ],
    install_requires=["setuptools", "roboweave-interfaces"],
    zip_safe=True,
    maintainer="RoboWeave",
    maintainer_email="roboweave@example.com",
    description="On-device task execution hub for RoboWeave",
    license="MIT",
    entry_points={
        "console_scripts": [
            "runtime_node = roboweave_runtime.runtime_node:main",
        ],
    },
)
