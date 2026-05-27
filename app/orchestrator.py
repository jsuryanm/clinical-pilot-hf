"""LangGraph orchestrator.

Day-0 contract:
  * Builds a graph that classifies the inbound task type and routes to the
    matching agent node.
  * Every branch terminates by calling the agent's `mocks.py` so the full
    flow demos end-to-end while real agents are still being built.

When A / B / C ship their real agents, swap the `agent_*_node` body for the
real call. The orchestrator itself does not change.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import structlog

from app.agents.appointment.mocks import fake_booking
from app.agents.clerical.mocks import fake_referral_letter
from app.agents.discharge.mocks import fake_discharge
from app.agents.documentation.mocks import fake_soap_draft
from app.agents.handover.mocks import fake_handover
from app.agents.roster.mocks import fake_roster
from app.contracts import RoutingDecision, TaskType
from app.llm.router import complete
from app.state import CliniqState, new_state

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Routing (LLM-backed with a deterministic fallback)
# ---------------------------------------------------------------------------


_ROUTE_PROMPT = """You are CliniqAI's orchestrator. Classify the user's request into one of:
  documentation, appointment, roster, handover, discharge, clerical, wiki_maintenance.

Return JSON: {"task": "<one of above>", "confidence": 0.0-1.0, "rationale": "<one short sentence>", "escalate": false}

Request:
{utterance}
"""


def _route_with_llm(utterance: str) -> RoutingDecision:
    try:
        resp = complete(
            task="routing",
            messages=[{"role": "user", "content": _ROUTE_PROMPT.format(utterance=utterance)}],
            json_mode=True,
            max_tokens=200,
        )
        data = json.loads(resp.text)
        return RoutingDecision(
            task=TaskType(data["task"]),
            confidence=float(data.get("confidence", 0.5)),
            rationale=str(data.get("rationale", "")),
            escalate=bool(data.get("escalate", False)),
        )
    except Exception:  # noqa: BLE001
        log.warning("orchestrator.llm_routing_failed_falling_back", exc_info=True)
        return _route_with_keywords(utterance)


def _route_with_keywords(utterance: str) -> RoutingDecision:
    u = utterance.lower()
    # Order matters — more specific phrases first to avoid keyword collisions
    # (e.g., "shift change" must hit HANDOVER before "shift" hits ROSTER).
    pairs = [
        (("handover", "shift change", "shift handover", "ward round"), TaskType.HANDOVER),
        (("book", "appointment", "reschedule", "cancel", "slot"), TaskType.APPOINTMENT),
        (("discharge", "going home", "leaving today"), TaskType.DISCHARGE),
        (("roster", "sick call", "leave request", "shift swap", "on-call"), TaskType.ROSTER),
        (("referral", "insurance", "faq", "followup", "follow-up"), TaskType.CLERICAL),
        (("guideline", "wiki", "update protocol"), TaskType.WIKI_MAINT),
    ]
    for keywords, t in pairs:
        if any(k in u for k in keywords):
            return RoutingDecision(task=t, confidence=0.6, rationale=f"keyword match: {keywords[0]}")
    return RoutingDecision(task=TaskType.DOCUMENTATION, confidence=0.4, rationale="default → documentation")


# ---------------------------------------------------------------------------
# Nodes (each returns the partial state delta it changes)
# ---------------------------------------------------------------------------


def orchestrator_node(state: CliniqState) -> dict[str, Any]:
    utt = ""
    if state.get("messages"):
        utt = state["messages"][-1].get("content", "")  # type: ignore[index]
    decision = _route_with_llm(utt) if utt else RoutingDecision(
        task=TaskType.DOCUMENTATION, confidence=0.0, rationale="empty input"
    )
    log.info("orchestrator.route", task=decision.task.value, conf=decision.confidence)
    return {"routing": decision, "task_type": decision.task, "current_agent": "orchestrator"}


def doc_node(state: CliniqState) -> dict[str, Any]:
    # TODO(Person A): replace with app.agents.documentation.api.draft_soap(...)
    draft = fake_soap_draft()
    return {"soap_draft": draft, "current_agent": "documentation"}


def appt_node(state: CliniqState) -> dict[str, Any]:
    # TODO(Person B): replace with app.agents.appointment.api.book(...)
    booking = fake_booking()
    return {"booking": booking, "current_agent": "appointment"}


def roster_node(state: CliniqState) -> dict[str, Any]:
    # TODO(Person C): replace with app.agents.roster.api.generate_roster(...)
    return {"roster": fake_roster(), "current_agent": "roster"}


def handover_node(state: CliniqState) -> dict[str, Any]:
    # TODO(Person C): replace with app.agents.handover.api.generate_handover(...)
    return {"handover": fake_handover(), "current_agent": "handover"}


def discharge_node(state: CliniqState) -> dict[str, Any]:
    # TODO(Person B): replace with app.agents.discharge.api.initiate_discharge(...)
    return {"discharge": fake_discharge(), "current_agent": "discharge"}


def clerical_node(state: CliniqState) -> dict[str, Any]:
    # TODO(Person B): replace with app.agents.clerical.api.draft_referral(...)
    return {"communication": fake_referral_letter(), "current_agent": "clerical"}


def wiki_maint_node(state: CliniqState) -> dict[str, Any]:
    # TODO(Person A): replace with app.agents.wiki.api.lint_wiki()
    return {"current_agent": "wiki_maintenance"}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


def _route_branch(state: CliniqState) -> str:
    r = state.get("routing")
    if r is None:
        return TaskType.DOCUMENTATION.value
    return r.task.value


def build_graph():
    """Build and compile the LangGraph state graph."""
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("langgraph is not installed — run `make install`") from e

    g = StateGraph(CliniqState)
    g.add_node("orchestrator", orchestrator_node)
    g.add_node(TaskType.DOCUMENTATION.value, doc_node)
    g.add_node(TaskType.APPOINTMENT.value, appt_node)
    g.add_node(TaskType.ROSTER.value, roster_node)
    g.add_node(TaskType.HANDOVER.value, handover_node)
    g.add_node(TaskType.DISCHARGE.value, discharge_node)
    g.add_node(TaskType.CLERICAL.value, clerical_node)
    g.add_node(TaskType.WIKI_MAINT.value, wiki_maint_node)

    g.add_edge(START, "orchestrator")
    g.add_conditional_edges("orchestrator", _route_branch, {
        TaskType.DOCUMENTATION.value: TaskType.DOCUMENTATION.value,
        TaskType.APPOINTMENT.value: TaskType.APPOINTMENT.value,
        TaskType.ROSTER.value: TaskType.ROSTER.value,
        TaskType.HANDOVER.value: TaskType.HANDOVER.value,
        TaskType.DISCHARGE.value: TaskType.DISCHARGE.value,
        TaskType.CLERICAL.value: TaskType.CLERICAL.value,
        TaskType.WIKI_MAINT.value: TaskType.WIKI_MAINT.value,
    })
    for t in TaskType:
        g.add_edge(t.value, END)

    return g.compile()


def run(utterance: str, session_id: str = "demo") -> CliniqState:
    """Synchronous one-shot helper for CLI / tests."""
    graph = build_graph()
    state = new_state(session_id)
    state["messages"] = [{"role": "user", "content": utterance}]
    return graph.invoke(state)  # type: ignore[return-value]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    out = run(sys.argv[1] if len(sys.argv) > 1 else "Please write a SOAP note for today's BP patient.")
    print(json.dumps({k: str(v) for k, v in out.items() if v is not None}, indent=2))
