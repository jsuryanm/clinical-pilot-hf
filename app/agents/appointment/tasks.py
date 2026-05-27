"""Celery app + reminder tasks. OWNER: Person B.

Run worker: `make worker`
Run beat:   `make beat`
"""

from __future__ import annotations

import os

from celery import Celery

app = Celery(
    "cliniqai",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)
app.conf.timezone = "Asia/Kolkata"


@app.task(name="appointment.send_reminder")
def send_reminder(appointment_id: str, channel: str) -> dict:
    """TODO(Person B): look up appointment, render localised message, dispatch."""
    return {"appointment_id": appointment_id, "channel": channel, "sent": False, "stub": True}


@app.task(name="appointment.post_discharge_followup")
def post_discharge_followup(patient_id: str) -> dict:
    """TODO(Person B): wired to discharge_time + 72h via beat schedule."""
    return {"patient_id": patient_id, "sent": False, "stub": True}
