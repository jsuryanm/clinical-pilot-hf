"""Wiki lint tests. OWNER: Person A — Day 8.

Points the wiki root at a tmp dir so we control the corpus under test.
"""

from __future__ import annotations

from app.agents.wiki import api as wiki_api


def _write(root, folder, name, text):
    d = root / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.md").write_text(text, encoding="utf-8")


def test_clean_page_has_no_issues(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLINIQ_WIKI_DIR", str(tmp_path))
    today = "2026-06-07"
    _write(tmp_path, "conditions", "hypertension", (
        f"---\ntype: condition\nid: hypertension\ntitle: HTN\n"
        f"last_updated: {today}\nsource: WHO\n---\n\n# HTN\n\nSee [[drugs/amlodipine]].\n"
    ))
    _write(tmp_path, "drugs", "amlodipine", (
        f"---\ntype: drug\nid: amlodipine\ntitle: Amlodipine\n"
        f"last_updated: {today}\nsource: BNF\n---\n\n# Amlodipine\n"
    ))

    report = wiki_api.lint_wiki()
    assert report.issues == []


def test_detects_missing_field_broken_xref_and_stale(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CLINIQ_WIKI_DIR", str(tmp_path))
    _write(tmp_path, "conditions", "bad", (
        "---\ntype: condition\nid: bad\nlast_updated: 2000-01-01\n---\n\n"
        "# Bad\n\nLinks to [[conditions/missing]].\n"
    ))

    report = wiki_api.lint_wiki()
    kinds = {i.kind for i in report.issues}
    assert "missing_field" in kinds  # no title, no source
    assert "stale" in kinds  # last_updated way in the past
    assert "broken_xref" in kinds  # target page does not exist
    assert all(i.page_path == "conditions/bad" for i in report.issues)
