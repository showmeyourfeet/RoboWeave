# RoboWeave: A VLM-Agent Driven Robotic Skill Orchestration System

[中文版](README_zh.md)

A hybrid robotics system architecture combining VLM-Agent, Skill Orchestration, and VLA for real-world robot deployment.

## Overview

RoboWeave decomposes robot tasks into layered, independently manageable subsystems: high-level semantic planning, on-device skill orchestration, specialized perception and geometry modules, VLA complex skills, low-level control, and a data feedback loop. VLA serves as a complex skill expert rather than the sole system controller.

## Architecture

```mermaid
flowchart TB
    classDef user fill:#dbeafe,stroke:#3b82f6,stroke-width:2px,color:#1e3a5f
    classDef cloud fill:#e0e7ff,stroke:#6366f1,stroke-width:2px,color:#312e81
    classDef runtime fill:#ccfbf1,stroke:#14b8a6,stroke-width:2px,color:#134e4a
    classDef skill fill:#dcfce7,stroke:#22c55e,stroke-width:2px,color:#14532d
    classDef vla fill:#f3e8ff,stroke:#a855f7,stroke-width:2px,color:#581c87
    classDef safety fill:#fee2e2,stroke:#ef4444,stroke-width:3px,color:#7f1d1d
    classDef data fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#78350f
    classDef hw fill:#f1f5f9,stroke:#64748b,stroke-width:2px,color:#1e293b

    U["🧑‍💻 User Input"]:::user
    CA["☁️ Cloud Agent<br/><sub>gRPC · LLM / VLM</sub>"]:::cloud
    RT["⚙️ Runtime<br/><sub>TaskExecutor · SkillOrchestrator · WorldModel</sub>"]:::runtime
    PER["👁️ Perception<br/><sub>Detection · Segmentation · PointCloud · Pose</sub>"]:::skill
    PL["📐 Planning<br/><sub>Grasp · IK · Collision · Motion</sub>"]:::skill
    VLA["🧠 VLA Skills<br/><sub>Learned Manipulation</sub>"]:::vla
    CTL["🎮 Control<br/><sub>Trajectory · Gripper · HW Abstraction</sub>"]:::skill
    SF["🛡️ Safety Supervisor<br/><sub>Independent Process</sub>"]:::safety
    HW["🤖 Robot Hardware"]:::hw
    DATA["📊 Data Collection<br/><sub>Episodes · Labels · Failure Mining</sub>"]:::data

    U -->|instruction| CA
    CA -->|PlanGraph| RT
    RT --> PER
    RT --> PL
    RT --> VLA
    RT --> CTL
    SF -.->|monitor & filter| CTL
    SF -.->|action filter| VLA
    CTL --> HW
    PER --> HW
    HW --> DATA
    DATA -.->|training loop| PER
    DATA -.->|training loop| VLA
```

## Packages

| Package | Type | Role |
|---|---|---|
| `roboweave_interfaces` | Pure Python | Pydantic data structures for all subsystems |
| `roboweave_msgs` | ROS2 IDL | msg / srv / action definitions |
| `roboweave_control` | ROS2 Node | Hardware abstraction, trajectory execution, gripper control |
| `roboweave_safety` | ROS2 Node (independent) | Safety supervisor (velocity/force/workspace monitoring, e-stop, VLA filtering) |
| `roboweave_runtime` | ROS2 Node | WorldModel, SkillOrchestrator, TaskExecutor, ExecutionMonitor |
| `roboweave_perception` | ROS2 Node | Detection, segmentation, point cloud, pose estimation (pluggable backends) |
| `roboweave_planning` | ROS2 Node | Grasp planning, IK, collision checking, motion planning (pluggable backends) |
| `roboweave_data` | ROS2 Node | Episode recording, labeling, failure mining, data export |
| `roboweave_cloud_agent` | Standalone gRPC | Cloud-side agent (task decomposition, recovery advice) |
| `roboweave_vla` | ROS2 Node | VLA skill framework with safety filtering |
| `roboweave_bringup` | ROS2 Launch | System launch orchestration |

## Quick Start

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up workspace
bash tools/scripts/setup_workspace.sh

# Verify installation
bash tools/scripts/verify_all.sh

# Run tests
bash tools/scripts/run_tests.sh
```

## Requirements

- Python 3.10+
- ROS2 Jazzy (Ubuntu 24.04) or Humble (Ubuntu 22.04)
- uv (Python package manager)

## License

[Apache-2.0](LICENSE)
