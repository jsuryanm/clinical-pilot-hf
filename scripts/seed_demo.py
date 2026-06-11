"""Seed the local database with enough demo rows for the Gradio UI to work."""

from __future__ import annotations

from app.db.session import SessionLocal
from app.db.models import Patient, Staff


def seed() -> None:
    with SessionLocal() as s:

        # --- Patients --------------------------------------------------------
        # Seed p-001 through p-010 (used by doctor tab, documentation demos).
        for i in range(1, 11):
            pid = f"p-{i:03d}"
            if not s.get(Patient, pid):
                s.add(Patient(id=pid, name=f"Demo Patient {i:03d}"))
                print(f"  + Patient {pid}")

        # Seed the patient that the Gradio chat widget derives from "demo-user".
        # PYTHONHASHSEED=0 must be set (Step 2) for this to be deterministic.
        demo_pid = f"p-{abs(hash('demo-user')) % 100000:05d}"
        if not s.get(Patient, demo_pid):
            s.add(Patient(id=demo_pid, name="Chat Demo User"))
            print(f"  + Patient {demo_pid}  (auto-derived from 'demo-user')")

        # --- Staff -----------------------------------------------------------
        staff_rows = [
            ("d-001", "Dr. Sharma", "doctor"),
            ("d-002", "Dr. Mehta",  "doctor"),
            ("n-01",  "Priya",      "nurse"),
            ("n-02",  "Anjali",     "nurse"),
            ("n-03",  "Ravi",       "nurse"),
        ]
        for sid, name, role in staff_rows:
            if not s.get(Staff, sid):
                s.add(Staff(id=sid, name=name, role=role))
                print(f"  + Staff   {sid}  {name}")

        s.commit()
        print("\n✅  Demo data seeded successfully.")


if __name__ == "__main__":
    seed()