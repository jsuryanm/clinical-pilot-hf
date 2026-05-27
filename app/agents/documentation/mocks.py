"""Realistic-but-fake Documentation Agent output.

OWNER: Person A — replace `fake_soap_draft` with the real agent on Day 3.
Person B and C may import this until A's real agent lands.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.contracts import (
    Citation,
    ICD10Suggestion,
    SOAPNoteDraft,
    SOAPSection,
)


def fake_soap_draft(patient_id: str = "p-001") -> SOAPNoteDraft:
    return SOAPNoteDraft(
        draft_id=f"soap-{uuid4().hex[:8]}",
        patient_id=patient_id,
        encounter_ts=datetime.now(timezone.utc),
        soap=SOAPSection(
            subjective=(
                "52-year-old male, known hypertensive on amlodipine 5 mg, presents with "
                "2-day history of frontal headache and intermittent dizziness. Denies "
                "chest pain, breathlessness, or visual changes."
            ),
            objective=(
                "BP 162/98 mmHg (R arm, seated), HR 84 regular, SpO2 99% RA, afebrile. "
                "Cardiovascular and neurological exam unremarkable."
            ),
            assessment=(
                "Uncontrolled essential hypertension, likely secondary to medication "
                "non-adherence over the last week. No end-organ red flags today."
            ),
            plan=(
                "1) Increase amlodipine to 10 mg OD. "
                "2) Add Telmisartan 40 mg OD. "
                "3) Home BP log twice daily x 2 weeks. "
                "4) Review in OPD on day 14 with BP chart. "
                "5) Counsel on salt restriction and adherence."
            ),
        ),
        icd10_suggestions=[
            ICD10Suggestion(code="I10", label="Essential (primary) hypertension", confidence=0.92),
            ICD10Suggestion(code="R51", label="Headache", confidence=0.71),
        ],
        guideline_suggestions=[
            "ICMR 2023 hypertension: consider ARB add-on when BP > 150/90 on monotherapy.",
        ],
        sources=[
            Citation(
                source_type="wiki",
                source_id="conditions/hypertension",
                title="Hypertension — Current Guideline",
                snippet="Stage-2 HTN: combination therapy preferred to maximising single agent.",
            ),
            Citation(
                source_type="wiki",
                source_id="patients/p-001",
                title="Patient p-001 — History",
                snippet="On amlodipine 5 mg since 2023. Last reviewed 2024-11.",
            ),
        ],
        referral_needed=False,
        confidence_overall=0.83,
        transcript_excerpt="Doctor: how's the BP at home? Patient: I stopped the tablet last week…",
        model="mock/stub",
    )
