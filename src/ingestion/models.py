from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class League(BaseModel):
    """Sleeper league metadata.

    Note: We extract key settings from nested 'settings' dict for easier access.
    """

    id: str = Field(..., alias="league_id")
    name: Optional[str] = None
    season: Optional[str] = None  # Year as string (e.g., "2025")
    total_rosters: Optional[int] = None  # Total number of teams in the league
    status: Optional[str] = None  # 'pre_draft', 'drafting', 'in_season', 'complete'

    # Nested settings (extracted in model_validate)
    playoff_teams: Optional[int] = None  # Number of teams making playoffs
    playoff_week_start: Optional[int] = None  # Week playoffs begin

    # Store full settings dict for advanced use cases
    settings: Optional[dict[str, Any]] = None
    scoring_settings: Optional[dict[str, Any]] = None
    roster_positions: Optional[list[str]] = None

    @classmethod
    def model_validate(cls, obj: Any, **kwargs) -> "League":
        """Override to extract settings from nested dict."""
        if isinstance(obj, dict) and "settings" in obj:
            # Extract commonly-used settings to top level
            settings = obj.get("settings", {})
            obj["playoff_teams"] = settings.get("playoff_teams")
            obj["playoff_week_start"] = settings.get("playoff_week_start")
        return super().model_validate(obj, **kwargs)


class User(BaseModel):
    id: str = Field(..., alias="user_id")
    display_name: Optional[str] = None


class Roster(BaseModel):
    roster_id: int
    owner_id: Optional[str] = None
    players: list[str] = Field(default_factory=list)


class Matchup(BaseModel):
    matchup_id: int
    roster_id: int
    points: float


class Transaction(BaseModel):
    id: str = Field(..., alias="transaction_id")
    status: Optional[str] = None
