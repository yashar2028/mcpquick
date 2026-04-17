from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        SQLEnum(
            RunStatus,
            name="run_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=RunStatus.QUEUED,
    )
    max_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=20)

    # Session-only key policy is enforced by never storing raw provider keys.
    api_key_provided: Mapped[bool] = mapped_column(nullable=False, default=False)

    requested_external_mcp_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_mcp_enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    sandbox_profile: Mapped[str] = mapped_column(
        String(128), nullable=False, default="nix-sandbox-v1"
    )

    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    evaluation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    events: Mapped[list[RunEvent]] = relationship(
        "RunEvent",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    user: Mapped[User] = relationship("User", back_populates="runs")


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    step_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    run: Mapped[EvaluationRun] = relationship("EvaluationRun", back_populates="events")
