from setuptools import find_packages, setup

package_name = "roboweave_vla"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["tests"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", [
            "config/vla_params.yaml",
            "config/vla_skill_registry.yaml",
        ]),
        ("share/" + package_name + "/launch", ["launch/vla.launch.py"]),
    ],
    install_requires=["setuptools", "roboweave-interfaces", "numpy"],
    zip_safe=True,
    maintainer="RoboWeave",
    maintainer_email="roboweave@example.com",
    description="VLA (Vision-Language-Action) skill framework for RoboWeave",
    license="MIT",
    entry_points={
        "console_scripts": [
            "vla_node = roboweave_vla.vla_node:main",
        ],
    },
)
