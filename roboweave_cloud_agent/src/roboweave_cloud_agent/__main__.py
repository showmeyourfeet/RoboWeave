"""Entry point: python -m roboweave_cloud_agent."""

from __future__ import annotations

import argparse
import logging
import os
import sys


def main() -> None:
    """Parse config path and start the gRPC server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="RoboWeave Cloud Agent gRPC Server"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to cloud_agent_params.yaml",
    )
    args = parser.parse_args()

    config_path = args.config or os.environ.get(
        "ROBOWEAVE_CLOUD_AGENT_CONFIG",
        "config/cloud_agent_params.yaml",
    )

    from .grpc_server import serve

    serve(config_path)


if __name__ == "__main__":
    main()
