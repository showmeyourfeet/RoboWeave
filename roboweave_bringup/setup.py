from setuptools import setup

package_name = "roboweave_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=[],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", [
            "launch/full_system.launch.py",
            "launch/sim_system.launch.py",
        ]),
        ("share/" + package_name + "/config", [
            "config/system_params.yaml",
        ]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="RoboWeave",
    maintainer_email="dev@roboweave.dev",
    description="System launch files for RoboWeave",
    license="Apache-2.0",
)
