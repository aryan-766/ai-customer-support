"""SQLAlchemy ORM models for PostgreSQL."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, Boolean, Float, Integer, Text, DateTime, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile:     Mapped[str]       = mapped_column(String(15), unique=True, nullable=False, index=True)
    email:      Mapped[str | None]= mapped_column(String(255))
    name:       Mapped[str | None]= mapped_column(String(255))
    is_vip:     Mapped[bool]      = mapped_column(Boolean, default=False)
    crm_id:     Mapped[str | None]= mapped_column(String(100))
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    calls:   "list[Call]"   = relationship("Call",   back_populates="customer")
    tickets: "list[Ticket]" = relationship("Ticket", back_populates="customer")


class Call(Base):
    __tablename__ = "calls"

    id:                Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id:       Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), index=True)
    channel:           Mapped[str]          = mapped_column(String(20), default="phone")
    language:          Mapped[str]          = mapped_column(String(5), default="en")
    status:            Mapped[str]          = mapped_column(String(20), default="active", index=True)
    started_at:        Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=now_utc)
    ended_at:          Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_sec:      Mapped[int | None]   = mapped_column(Integer)

    # Auth
    auth_method:       Mapped[str | None]   = mapped_column(String(50))
    is_authenticated:  Mapped[bool]         = mapped_column(Boolean, default=False)

    # Intent & routing
    detected_intent:   Mapped[str | None]   = mapped_column(String(100))
    intent_confidence: Mapped[float | None] = mapped_column(Float)
    routing_path:      Mapped[list]         = mapped_column(JSON, default=list)

    # Intelligence
    sentiment:         Mapped[str | None]   = mapped_column(String(20))
    sentiment_score:   Mapped[float | None] = mapped_column(Float)
    ai_confidence:     Mapped[float | None] = mapped_column(Float)
    priority:          Mapped[str | None]   = mapped_column(String(20))
    fraud_score:       Mapped[float | None] = mapped_column(Float)

    # Resolution
    resolved:          Mapped[bool]         = mapped_column(Boolean, default=False)
    resolution_type:   Mapped[str | None]   = mapped_column(String(50))
    zoho_ticket_id:    Mapped[str | None]   = mapped_column(String(100))
    human_agent_id:    Mapped[str | None]   = mapped_column(String(100))

    # Content
    transcript:        Mapped[list]         = mapped_column(JSON, default=list)
    ai_summary:        Mapped[str | None]   = mapped_column(Text)
    citations:         Mapped[list]         = mapped_column(JSON, default=list)
    follow_up_tasks:   Mapped[list]         = mapped_column(JSON, default=list)

    created_at:        Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=now_utc)

    customer: "Customer" = relationship("Customer", back_populates="calls")
    tickets:  "list[Ticket]" = relationship("Ticket", back_populates="call")


class Ticket(Base):
    __tablename__ = "tickets"

    id:             Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zoho_ticket_id: Mapped[str | None]     = mapped_column(String(100), unique=True)
    call_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"))
    customer_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"))
    subject:        Mapped[str | None]     = mapped_column(String(500))
    status:         Mapped[str | None]     = mapped_column(String(50), default="open")
    priority:       Mapped[str | None]     = mapped_column(String(20))
    department:     Mapped[str | None]     = mapped_column(String(100))
    created_at:     Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at:     Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    call:     "Call"     = relationship("Call",     back_populates="tickets")
    customer: "Customer" = relationship("Customer", back_populates="tickets")


class KBDocument(Base):
    __tablename__ = "kb_documents"

    id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title:       Mapped[str]       = mapped_column(String(500), nullable=False)
    category:    Mapped[str | None]= mapped_column(String(100), index=True)
    source_file: Mapped[str | None]= mapped_column(String(500))
    qdrant_ids:  Mapped[list]      = mapped_column(JSON, default=list)
    ingested_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=now_utc)
    version:     Mapped[int]       = mapped_column(Integer, default=1)


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id:          Mapped[int]       = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id:     Mapped[str | None]= mapped_column(String(100), index=True)
    event_type:  Mapped[str | None]= mapped_column(String(100), index=True)
    event_data:  Mapped[dict]      = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
