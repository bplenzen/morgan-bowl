from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class League(BaseModel):
    id: str = Field(..., alias="league_id")
    name: Optional[str] = None


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
