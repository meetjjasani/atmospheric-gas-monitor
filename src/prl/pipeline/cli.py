from __future__ import annotations

import argparse
from pathlib import Path

from prl.core.services.pipeline_service import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="CRDS UTC->IST data pipeline")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/config.json"),
        help="Path to JSON config",
    )
    args = parser.parse_args()
    master_path = run_pipeline(args.config)
    print(f"Pipeline finished. Master output: {master_path}")


if __name__ == "__main__":
    main()
