#!/bin/bash
# Quick verification: import all packages and run basic smoke tests
set -e

PYTHON=".venv/bin/python"

echo "=== RoboWeave Quick Verification ==="

$PYTHON -c "
import numpy as np

# Phase 0
from roboweave_interfaces import WorldState, RobotState, ErrorCode, ERROR_CODE_SPECS, SE3
print(f'  interfaces: {len(ErrorCode)} error codes, {len(ERROR_CODE_SPECS)} specs')

# Phase 1
from roboweave_control.drivers.sim_driver import SimDriver
from roboweave_safety.safety_guard import SafetyGuard
from roboweave_safety.safety_monitor import SafetyMonitor
from roboweave_runtime.world_model import WorldModel
from roboweave_runtime.resource_manager import ResourceManager
from roboweave_runtime.execution_monitor import ExecutionMonitor
print('  control + safety + runtime: OK')

# Phase 2
from roboweave_perception.backend_registry import get_backend as p_get
import roboweave_perception.backends
det = p_get('detector', 'mock')
r = det.detect(np.zeros((100,100,3), dtype=np.uint8), 'cup')
assert len(r) == 1
print('  perception: OK')

from roboweave_planning.backend_registry import get_backend as pl_get
import roboweave_planning.backends
ik = pl_get('ik_solver', 'mock')
mp = pl_get('motion_planner', 'simple', ik_solver=ik)
from roboweave_interfaces.motion import MotionRequest
result = mp.plan(MotionRequest(arm_id='a1', goal_joint_state=[1.0]*6, planning_mode='joint_space'), [0.0]*6)
assert len(result.trajectory) >= 10
print('  planning: OK')

# Phase 3
from roboweave_data.episode_recorder import EpisodeRecorder
from roboweave_data.label_generator import LabelGenerator
from roboweave_data.failure_miner import FailureMiner
print('  data: OK')

# Phase 4
from roboweave_cloud_agent.agent import Agent
from roboweave_cloud_agent.skill_selector import SkillSelector
from roboweave_cloud_agent.recovery_advisor import RecoveryAdvisor
print('  cloud_agent: OK')

# Phase 5
from roboweave_vla.vla_monitor import VLAMonitor
from roboweave_vla.skill_registry import SkillRegistry
from roboweave_vla.skills.fold_cloth import MockFoldClothSkill
print('  vla: OK')

print()
print('ALL 9 PACKAGES VERIFIED')
"

echo ""
echo "=== Verification Complete ==="
