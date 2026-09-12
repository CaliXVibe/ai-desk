"""Deterministic Night Desk ingest. Same three artifacts as the prompt.

This is a local heuristic so the demo needs no API keys. For model-backed
ingest, use prompts/night-desk.md.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

DATE_RE = re.compile(
    r"\b(20\d{2}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?\b"
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
DURATION_RE = re.compile(r"\b(\d+)\s*minutes?\b", re.I)


def _slug(title: str) -> str:
    raw = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return (raw or "job")[:48]


def _title(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("client:"):
            name = line.split(":", 1)[1].strip()
            if name:
                return name
        if not line.lower().startswith(("contact:", "notes:", "open:")):
            clipped = line[:80]
            return clipped
    return "Untitled job"


def _when(text: str, now: datetime) -> tuple[datetime, datetime, str]:
    duration = timedelta(minutes=45)
    match = DURATION_RE.search(text)
    if match:
        duration = timedelta(minutes=int(match.group(1)))

    found = DATE_RE.search(text)
    if found:
        day = datetime.strptime(found.group(1), "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        if found.group(2):
            hour, minute = found.group(2).split(":")
            start = day.replace(hour=int(hour), minute=int(minute))
        else:
            start = day.replace(hour=9, minute=0)
        return start, start + duration, "Date taken from job text."

    start = (now + timedelta(hours=24)).replace(minute=0, second=0, microsecond=0)
    return (
        start,
        start + duration,
        "No date in source; scheduled as a triage block.",
    )


def ingest(job_text: str, target_user: str, *, now: datetime | None = None) -> dict[str, Any]:
    text = (job_text or "").strip()
    if not target_user:
        raise ValueError("target_user is required")
    if not text:
        raise ValueError("job_text is empty")

    clock = now or datetime.now(timezone.utc)
    title = _title(text)
    slug = _slug(title)
    emails = EMAIL_RE.findall(text)
    contact = emails[0] if emails else "unassigned"
    start, end, cal_notes = _when(text, clock)

    people = ", ".join(emails) if emails else "none listed"
    markdown = "\n".join(
        [
            f"# {title}",
            "",
            "## Summary",
            text.splitlines()[0].strip() if text.splitlines() else title,
            "",
            "## People",
            people,
            "",
            "## Dates",
            f"- start: {start.isoformat()}",
            f"- end: {end.isoformat()}",
            "",
            "## Action items",
            "- Review the brief and confirm the slot.",
            "",
            "## Open questions",
            "- " + cal_notes,
            "",
            "## Source",
            "```",
            text,
            "```",
            "",
        ]
    )

    return {
        "target_user": target_user,
        "mail": {
            "from": "night-desk@local",
            "to": contact,
            "subject": f"Job brief: {title}",
            "body": f"Night Desk filed this job for {target_user}.\n\n{text}",
        },
        "file": {
            "path": f"jobs/{slug}.md",
            "markdown": markdown,
        },
        "calendar": {
            "title": title,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "notes": cal_notes,
        },
    }
