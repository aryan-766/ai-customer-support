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

    calls:   Mapped["list[Call]"]   = relationship("Call",   back_populates="customer")
    tickets: Mapped["list[Ticket]"] = relationship("Ticket", back_populates="customer")
    orders:  Mapped["list[Order]"]  = relationship("Order",  back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id:             Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"))
    order_number:   Mapped[str]            = mapped_column(String(100), unique=True, index=True)
    status:         Mapped[str]            = mapped_column(String(50), default="processing")
    total_amount:   Mapped[float | None]   = mapped_column(Float)
    created_at:     Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at:     Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")


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
    human_agent_id:    Mapped[str | None]   = mapped_column(String(100))
    ai_summary:        Mapped[str | None]   = mapped_column(Text)
    
    created_at:        Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=now_utc)

    customer:    Mapped["Customer"]           = relationship("Customer", back_populates="calls")
    tickets:     Mapped["list[Ticket]"]       = relationship("Ticket", back_populates="call")
    transcripts: Mapped["list[Transcript]"]   = relationship("Transcript", back_populates="call")
    messages:    Mapped["list[Message]"]      = relationship("Message", back_populates="call")
    agent_logs:  Mapped["list[AgentLog]"]     = relationship("AgentLog", back_populates="call")
    tool_logs:   Mapped["list[ToolLog]"]      = relationship("ToolLog", back_populates="call")
    call_summary:Mapped["CallSummary"]        = relationship("CallSummary", back_populates="call", uselist=False)


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

    call:     Mapped["Call"]     = relationship("Call",     back_populates="tickets")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="tickets")


class Transcript(Base):
    __tablename__ = "transcripts"
    
    id:          Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id:     Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"), index=True)
    role:        Mapped[str]            = mapped_column(String(20))  # human or ai
    text:        Mapped[str]            = mapped_column(Text)
    created_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=now_utc)
    
    call: Mapped["Call"] = relationship("Call", back_populates="transcripts")


class Message(Base):
    """LangGraph raw state messages"""
    __tablename__ = "messages"
    
    id:          Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id:     Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"), index=True)
    node:        Mapped[str]            = mapped_column(String(100))
    content:     Mapped[dict]           = mapped_column(JSON) # Store raw BaseMessage dict
    created_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=now_utc)
    
    call: Mapped["Call"] = relationship("Call", back_populates="messages")


class AgentLog(Base):
    __tablename__ = "agent_logs"
    
    id:          Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id:     Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"), index=True)
    agent_name:  Mapped[str]            = mapped_column(String(100))
    action:      Mapped[str]            = mapped_column(String(255))
    latency_ms:  Mapped[int | None]     = mapped_column(Integer)
    created_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=now_utc)
    
    call: Mapped["Call"] = relationship("Call", back_populates="agent_logs")


class CallSummary(Base):
    __tablename__ = "call_summaries"
    
    id:             Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id:        Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"), index=True, unique=True)
    summary_text:   Mapped[str]            = mapped_column(Text)
    customer_intent:Mapped[str | None]     = mapped_column(String(100))
    resolution:     Mapped[str | None]     = mapped_column(String(100))
    created_at:     Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=now_utc)
    
    call: Mapped["Call"] = relationship("Call", back_populates="call_summary")


class ToolLog(Base):
    __tablename__ = "tool_logs"
    
    id:          Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id:     Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id"), index=True)
    tool_name:   Mapped[str]            = mapped_column(String(100))
    inputs:      Mapped[dict]           = mapped_column(JSON, default=dict)
    outputs:     Mapped[dict]           = mapped_column(JSON, default=dict)
    success:     Mapped[bool]           = mapped_column(Boolean, default=True)
    latency_ms:  Mapped[int | None]     = mapped_column(Integer)
    created_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=now_utc)
    
    call: Mapped["Call"] = relationship("Call", back_populates="tool_logs")


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

