"""gRPC server and CloudAgentServicer for roboweave_cloud_agent.

Uses try/except for grpcio imports so the module can be imported
in environments where grpcio is not installed.
"""

from __future__ import annotations

import logging
import signal
import types
from typing import Any, Iterator

from .agent import Agent
from .converters import event_from_proto, plan_graph_to_proto

logger = logging.getLogger(__name__)

try:
    import grpc
    from concurrent import futures

    _GRPC_AVAILABLE = True
except ImportError:
    _GRPC_AVAILABLE = False


class CloudAgentServicer:
    """gRPC servicer — thin shell delegating to Agent."""

    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    def SubmitTask(self, request: Any, context: Any) -> types.SimpleNamespace:
        """Handle unary SubmitTask RPC."""
        instruction = getattr(request, "instruction", "")
        if not instruction:
            return types.SimpleNamespace(
                response_type=3,  # ERROR
                plan=None,
                error_message="instruction is required",
                clarification=None,
            )

        task_id = getattr(request, "task_id", "")
        scene_context = None
        sc = getattr(request, "scene_context", None)
        if sc is not None:
            scene_context = {
                "scene_id": getattr(sc, "scene_id", ""),
                "robot_id": getattr(sc, "robot_id", ""),
            }

        plan_graph = self._agent.decompose_task(instruction, task_id, scene_context)

        if plan_graph is None:
            return types.SimpleNamespace(
                response_type=1,  # REJECTION
                plan=None,
                error_message="instruction not recognized",
                clarification=None,
            )

        plan_proto = plan_graph_to_proto(plan_graph)
        return types.SimpleNamespace(
            response_type=0,  # PLAN
            plan=plan_proto,
            error_message="",
            clarification=None,
        )

    def SubmitTaskStream(
        self, request: Any, context: Any
    ) -> Iterator[types.SimpleNamespace]:
        """Handle server-streaming SubmitTaskStream RPC."""
        # Yield initial STATUS_UPDATE
        if hasattr(context, "is_active") and not context.is_active():
            return

        yield types.SimpleNamespace(
            event_type=0,  # STATUS_UPDATE
            message="Processing task...",
            plan=None,
            clarification=None,
            is_final=False,
        )

        instruction = getattr(request, "instruction", "")
        task_id = getattr(request, "task_id", "")

        if not instruction:
            yield types.SimpleNamespace(
                event_type=2,  # ERROR_OCCURRED
                message="instruction is required",
                plan=None,
                clarification=None,
                is_final=True,
            )
            return

        plan_graph = self._agent.decompose_task(instruction, task_id)

        if hasattr(context, "is_active") and not context.is_active():
            return

        if plan_graph is None:
            yield types.SimpleNamespace(
                event_type=2,  # ERROR_OCCURRED
                message="instruction not recognized",
                plan=None,
                clarification=None,
                is_final=True,
            )
        else:
            plan_proto = plan_graph_to_proto(plan_graph)
            yield types.SimpleNamespace(
                event_type=1,  # PLAN_COMPLETE
                message="Task decomposition complete",
                plan=plan_proto,
                clarification=None,
                is_final=True,
            )

    def AnalyzeFailure(self, request: Any, context: Any) -> types.SimpleNamespace:
        """Handle unary AnalyzeFailure RPC."""
        event_proto = getattr(request, "event", None)
        if event_proto is None:
            return types.SimpleNamespace(
                analysis="No event provided",
                recovery_actions=[],
                rationale_summary="",
            )

        event = event_from_proto(event_proto)
        analysis, recovery_actions = self._agent.analyze_failure(event)

        return types.SimpleNamespace(
            analysis=analysis,
            recovery_actions=recovery_actions,
            rationale_summary=analysis,
        )

    def UpdateWorldState(self, request: Any, context: Any) -> types.SimpleNamespace:
        """Handle unary UpdateWorldState RPC."""
        robot_id = getattr(request, "robot_id", "")
        ref_uri = getattr(request, "ref_uri", "")
        timestamp = getattr(request, "timestamp", 0.0)

        accepted = self._agent.update_world_state(robot_id, ref_uri, timestamp)

        msg = "accepted" if accepted else "rejected: robot_id is required"
        return types.SimpleNamespace(accepted=accepted, message=msg)


def serve(config_path: str) -> None:
    """Load config, create Agent, start gRPC server, handle signals.

    Requires grpcio to be installed.
    """
    if not _GRPC_AVAILABLE:
        raise RuntimeError(
            "grpcio is not installed. Install it with: pip install grpcio"
        )

    from .config import load_config

    config = load_config(config_path)
    agent = Agent(config)
    servicer = CloudAgentServicer(agent)

    server_config = config.get("server", {})
    host = server_config.get("host", "0.0.0.0")
    port = server_config.get("port", 50051)
    shutdown_timeout = server_config.get("shutdown_timeout_sec", 5)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Note: In production, you'd register the servicer with the generated
    # pb2_grpc module. For MVP, we just add the insecure port.
    address = f"{host}:{port}"
    server.add_insecure_port(address)
    server.start()
    logger.info(f"CloudAgentService listening on {address}")

    # Graceful shutdown on SIGINT/SIGTERM
    shutdown_event = None
    try:
        import threading

        shutdown_event = threading.Event()

        def _signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            shutdown_event.set()

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        shutdown_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop(grace=shutdown_timeout)
        logger.info("Server stopped.")
