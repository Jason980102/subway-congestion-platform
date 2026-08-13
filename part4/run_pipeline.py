"""Orchestrate repeat-safe data loading and candidate-model retraining."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import func, select, text

from database import SessionLocal
from load_data import load_ridership
from models import Ridership
from train_model import train_and_save


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_LOG_DIR = PROJECT_DIR / "artifacts" / "pipeline_runs"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, Path)):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def check_database() -> dict[str, Any]:
    with SessionLocal() as session:
        database_name = session.scalar(text("SELECT current_database()"))
        row_count = session.scalar(select(func.count()).select_from(Ridership))
    return {
        "database": str(database_name),
        "ridership_rows_before": int(row_count or 0),
    }


def verify_database() -> dict[str, int]:
    with SessionLocal() as session:
        row_count = session.scalar(select(func.count()).select_from(Ridership))
        distinct_station_count = session.scalar(
            select(func.count(func.distinct(Ridership.station_id)))
        )
        distinct_label_count = session.scalar(
            select(func.count(func.distinct(Ridership.congestion_level)))
        )
    return {
        "ridership_rows_after": int(row_count or 0),
        "distinct_stations": int(distinct_station_count or 0),
        "distinct_congestion_levels": int(distinct_label_count or 0),
    }


def run_stage(name: str, action: Callable[[], Any]) -> tuple[dict[str, Any], Any]:
    started = utc_now()
    print(f"[{started:%Y-%m-%d %H:%M:%S} UTC] Starting: {name}")
    stage: dict[str, Any] = {
        "name": name,
        "started_at": started.isoformat(),
        "status": "running",
    }
    started_clock = time.perf_counter()
    try:
        result = action()
    except Exception as exc:
        stage.update(
            status="failed",
            finished_at=utc_now().isoformat(),
            duration_seconds=round(time.perf_counter() - started_clock, 3),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        print(f"Stage failed: {name}: {exc}")
        return stage, exc

    stage.update(
        status="succeeded",
        finished_at=utc_now().isoformat(),
        duration_seconds=round(time.perf_counter() - started_clock, 3),
        result=json_safe(result),
    )
    print(f"Completed: {name}")
    return stage, result


def write_log(payload: dict[str, Any], log_directory: Path) -> Path:
    log_directory.mkdir(parents=True, exist_ok=True)
    run_id = str(payload["run_id"])
    path = log_directory / f"pipeline_{run_id}.json"
    path.write_text(json.dumps(json_safe(payload), indent=2), encoding="utf-8")
    return path


def run_pipeline(log_directory: Path = DEFAULT_LOG_DIR) -> Path:
    started = utc_now()
    payload: dict[str, Any] = {
        "run_id": started.strftime("%Y%m%d_%H%M%S_utc"),
        "started_at": started.isoformat(),
        "status": "running",
        "stages": [],
    }

    stages: list[tuple[str, Callable[[], Any]]] = [
        ("database_connectivity", check_database),
        ("repeat_safe_etl", load_ridership),
        ("candidate_model_retraining", train_and_save),
        ("post_run_verification", verify_database),
    ]

    failed: Exception | None = None
    try:
        for name, action in stages:
            stage, result = run_stage(name, action)
            payload["stages"].append(stage)
            if isinstance(result, Exception):
                failed = result
                break
    finally:
        payload["finished_at"] = utc_now().isoformat()
        payload["status"] = "failed" if failed else "succeeded"
        log_path = write_log(payload, log_directory)
        print(f"Pipeline status: {payload['status']}")
        print(f"Audit log: {log_path}")

    if failed:
        raise failed
    return log_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repeat-safe ETL, candidate retraining, and verification."
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help="Directory for timestamped JSON pipeline logs.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    try:
        run_pipeline(arguments.log_dir)
    except Exception:
        sys.exit(1)
