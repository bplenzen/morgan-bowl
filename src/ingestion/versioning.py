from __future__ import annotations

import json
import pathlib
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Sequence

import structlog

logger = structlog.get_logger("morgan_bowl.versioning")


class VersionStatus(str, Enum):
    """Status of a data version run."""

    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class DataVersion:
    """Track data versions for incremental loads and backfills."""

    timestamp: datetime
    run_id: str
    is_backfill: bool
    start_week: int
    end_week: int
    season: int
    weeks: Sequence[int]
    status: VersionStatus = VersionStatus.IN_PROGRESS
    error: Optional[str] = None

    @classmethod
    def create(
        cls,
        *,
        run_id: Optional[str] = None,
        is_backfill: bool = False,
        weeks: Sequence[int],
        season: int = 2025,
    ) -> DataVersion:
        """Create a new data version.

        Args:
            run_id: Optional unique identifier for this run
            is_backfill: Whether this is a backfill run
            weeks: Sequence of weeks being loaded
            season: Fantasy football season year

        Returns:
            New DataVersion instance
        """
        if run_id is None:
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        if not weeks:
            raise ValueError("Must provide at least one week")

        return cls(
            timestamp=datetime.now(),
            run_id=run_id,
            is_backfill=is_backfill,
            start_week=min(weeks),
            end_week=max(weeks),
            season=season,
            weeks=sorted(weeks),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> DataVersion:
        """Create instance from dictionary."""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["status"] = VersionStatus(data["status"])
        return cls(**data)

    def mark_success(self) -> None:
        """Mark this version as successfully completed."""
        object.__setattr__(self, "status", VersionStatus.SUCCESS)
        logger.info(
            "version_success",
            run_id=self.run_id,
            weeks=self.weeks,
            season=self.season,
        )

    def mark_failed(self, error: str) -> None:
        """Mark this version as failed with error message."""
        object.__setattr__(self, "status", VersionStatus.FAILED)
        object.__setattr__(self, "error", error)
        logger.error(
            "version_failed",
            run_id=self.run_id,
            weeks=self.weeks,
            season=self.season,
            error=error,
        )


class VersionStore:
    """Store and retrieve data versions."""

    def __init__(self, data_dir: str | pathlib.Path):
        self.data_dir = pathlib.Path(data_dir)
        self.versions_file = self.data_dir / "versions.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save_version(self, version: DataVersion) -> None:
        """Save a version to the store."""
        versions = self.load_versions()
        versions.append(version.to_dict())

        with self.versions_file.open("w") as f:
            json.dump(versions, f, indent=2)

        logger.info(
            "version_saved",
            run_id=version.run_id,
            file=str(self.versions_file),
        )

    def load_versions(self) -> list[dict]:
        """Load all versions from the store."""
        if not self.versions_file.exists():
            return []

        with self.versions_file.open() as f:
            try:
                return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(
                    "failed_to_load_versions",
                    file=str(self.versions_file),
                    error=str(e),
                )
                return []

    def get_latest_version(self) -> Optional[DataVersion]:
        """Get the most recent successful version."""
        versions = [DataVersion.from_dict(v) for v in self.load_versions()]

        successful = [v for v in versions if v.status == VersionStatus.SUCCESS]

        if not successful:
            return None

        return max(successful, key=lambda v: v.timestamp)
