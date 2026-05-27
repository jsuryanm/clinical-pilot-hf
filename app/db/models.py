"""SQLAlchemy models. Owned by Person C.

Tables chosen for the Week 1 + Week 2 MVP. Wiki content lives on disk,
ChromaDB lives outside Postgres — this layer stores transactional state
that needs SQL semantics (joins, audit, time-window queries).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Reference / master data
# ---------------------------------------------------------------------------


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # e.g. "p-001"
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20))
    dob: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    abha_id: Mapped[str | None] = mapped_column(String(20), index=True)
    wiki_page_path: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    appointments: Mapped[list[Appointment]] = relationship(back_populates="patient")
    messages: Mapped[list[Message]] = relationship(back_populates="patient")


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))  # doctor | nurse | tech | admin
    certifications: Mapped[list[str]] = mapped_column(JSON, default=list)
    max_hours_per_week: Mapped[int] = mapped_column(Integer, default=48)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    shifts: Mapped[list[Shift]] = relationship(back_populates="staff")


# ---------------------------------------------------------------------------
# Operational data
# ---------------------------------------------------------------------------


class BookingStatusEnum(str, Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    COMPLETED = "completed"
    WAITLISTED = "waitlisted"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[str] = mapped_column(String(32), index=True)
    slot_iso: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=15)
    status: Mapped[BookingStatusEnum] = mapped_column(
        SAEnum(BookingStatusEnum, name="booking_status"), default=BookingStatusEnum.PROPOSED
    )
    calendar_event_id: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    patient: Mapped[Patient] = relationship(back_populates="appointments")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    patient_id: Mapped[str | None] = mapped_column(ForeignKey("patients.id"), index=True)
    appointment_id: Mapped[str | None] = mapped_column(ForeignKey("appointments.id"))
    channel: Mapped[str] = mapped_column(String(20))  # whatsapp | email | web | phone
    direction: Mapped[str] = mapped_column(String(8))  # inbound | outbound
    body: Mapped[str] = mapped_column(Text)
    approved_by: Mapped[str | None] = mapped_column(String(32))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    patient: Mapped[Patient | None] = relationship(back_populates="messages")


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    staff_id: Mapped[str] = mapped_column(ForeignKey("staff.id"), index=True)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    role: Mapped[str] = mapped_column(String(20))
    is_replacement: Mapped[bool] = mapped_column(Boolean, default=False)

    staff: Mapped[Staff] = relationship(back_populates="shifts")


class Discharge(Base):
    __tablename__ = "discharges"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    target_complete_by: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    subtasks: Mapped[dict] = mapped_column(JSON, default=dict)


class SoapDraft(Base):
    __tablename__ = "soap_drafts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    encounter_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON)  # full SOAPNoteDraft.model_dump()
    approved_by: Mapped[str | None] = mapped_column(String(32))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(64))  # user_id, "system", or agent name
    action: Mapped[str] = mapped_column(String(64), index=True)
    target_type: Mapped[str | None] = mapped_column(String(32))
    target_id: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
