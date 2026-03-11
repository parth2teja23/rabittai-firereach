"""
Pydantic models for FireReach API request/response schemas.
All data validation is centralised here so FastAPI can auto-generate
the OpenAPI spec and the frontend always knows the contract.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AgentStatus(str, Enum):
    """Tracks each reasoning step the agent takes."""

    STARTED = "started"
    HARVESTING = "harvesting"
    RESEARCHING = "researching"
    SENDING = "sending"
    DONE = "done"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Request / Response shapes
# ---------------------------------------------------------------------------


class OutreachRequest(BaseModel):
    """
    Payload sent by the React frontend to kick off an outreach run.

    Fields:
        icp         – Ideal Customer Profile description,
                      e.g. "We sell high-end cybersecurity training to Series B startups."
        company     – The target company to research.
        to_email    – Recipient email address (used in both research & send steps).
        sender_name – How the sender should sign the email.
    """

    icp: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Ideal Customer Profile – who YOU are and what you sell.",
        examples=["We sell high-end cybersecurity training to Series B startups."],
    )
    company: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Target company name to research.",
        examples=["Acme Corp"],
    )
    to_email: EmailStr = Field(
        ...,
        description="Recipient email address for the outreach.",
    )
    sender_name: str = Field(
        default="FireReach AI",
        max_length=100,
        description="Name used in the email sign-off.",
    )


class SignalResult(BaseModel):
    """
    Output from tool_signal_harvester.
    Contains structured signals discovered via live web search.
    """

    company: str
    signals: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of signal objects with keys: type, summary, source_url.",
    )
    raw_summary: str = Field(
        description="Human-readable paragraph summarising all discovered signals."
    )


class AccountBrief(BaseModel):
    """
    Output from tool_research_analyst.
    A concise 2-paragraph brief that connects signals to the seller's ICP.
    """

    pain_points: str = Field(description="Paragraph 1 – detected pain points.")
    strategic_alignment: str = Field(
        description="Paragraph 2 – how the ICP maps to those pain points."
    )
    full_brief: str = Field(description="Both paragraphs combined.")


class EmailResult(BaseModel):
    """
    Output from tool_outreach_automated_sender.
    Carries both the generated email content and delivery metadata.
    """

    subject: str
    body: str
    to_email: str
    sent: bool = False
    message_id: str | None = None
    error: str | None = None


class AgentStep(BaseModel):
    """
    A single event emitted by the agent while it is running.
    The frontend renders these in real-time as a reasoning log.
    """

    status: AgentStatus
    tool_name: str | None = None
    message: str
    data: dict[str, Any] | None = None


class OutreachResponse(BaseModel):
    """
    Final response returned to the frontend after the full agent run.
    """

    success: bool
    steps: list[AgentStep] = Field(default_factory=list)
    signals: SignalResult | None = None
    brief: AccountBrief | None = None
    email: EmailResult | None = None
    error: str | None = None
