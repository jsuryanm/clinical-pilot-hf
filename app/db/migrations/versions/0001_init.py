"""initial schema

Revision ID: 0001_init
Revises:
Create Date: 2026-05-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("dob", sa.DateTime(timezone=True)),
        sa.Column("abha_id", sa.String(20), index=True),
        sa.Column("wiki_page_path", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "staff",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("certifications", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("max_hours_per_week", sa.Integer(), nullable=False, server_default="48"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    booking_status = sa.Enum(
        "proposed", "confirmed", "cancelled", "no_show", "completed", "waitlisted",
        name="booking_status",
    )
    booking_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "appointments",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("patient_id", sa.String(32), sa.ForeignKey("patients.id"), index=True),
        sa.Column("doctor_id", sa.String(32), index=True),
        sa.Column("slot_iso", sa.DateTime(timezone=True), index=True, nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("status", booking_status, nullable=False, server_default="proposed"),
        sa.Column("calendar_event_id", sa.String(120)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("patient_id", sa.String(32), sa.ForeignKey("patients.id"), index=True),
        sa.Column("appointment_id", sa.String(32), sa.ForeignKey("appointments.id")),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("approved_by", sa.String(32)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "shifts",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("staff_id", sa.String(32), sa.ForeignKey("staff.id"), index=True),
        sa.Column("start", sa.DateTime(timezone=True), index=True, nullable=False),
        sa.Column("end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_replacement", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "discharges",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("patient_id", sa.String(32), sa.ForeignKey("patients.id"), index=True),
        sa.Column("initiated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("target_complete_by", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("subtasks", sa.JSON(), nullable=False, server_default="{}"),
    )

    op.create_table(
        "soap_drafts",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("patient_id", sa.String(32), sa.ForeignKey("patients.id"), index=True),
        sa.Column("encounter_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("approved_by", sa.String(32)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), index=True, nullable=False),
        sa.Column("target_type", sa.String(32)),
        sa.Column("target_id", sa.String(64)),
        sa.Column("detail", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    for t in [
        "audit_log", "soap_drafts", "discharges", "shifts",
        "messages", "appointments", "staff", "patients",
    ]:
        op.drop_table(t)
    sa.Enum(name="booking_status").drop(op.get_bind(), checkfirst=True)
