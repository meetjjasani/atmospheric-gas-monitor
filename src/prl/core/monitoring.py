from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_pipeline_logging(log_dir: Path) -> logging.Logger:
    """Setup a high-fidelity logger for the pipeline execution.
    
    Creates a dedicated 'pipeline.log' file for traceability.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "pipeline.log"
    
    logger = logging.getLogger("prl.pipeline")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger
        
    # File handler (Rotation/Retention can be added later if needed)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    
    # Console handler (for terminal visibility during dev)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

def get_pipeline_logger() -> logging.Logger:
    """Convenience getter for the pipeline logger."""
    return logging.getLogger("prl.pipeline")
