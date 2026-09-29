import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from harmness.measure import SEVERITY_WEIGHT, measure, score
from harmness.models import Finding, Report

REPORT_VERSION = 1


class ReportError(ValueError):
    """A saved auto-test report is missing or cannot be read."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_report(target: Path, text: str) -> Report:
    return Report(
        target=str(target.resolve()),
        sha256=file_sha256(target),
        tested_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        findings=measure(text),
    )


def save_report(report: Report, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report_to_dict(report), indent=2) + "\n", encoding="utf-8")


def load_report(path: Path) -> Report:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReportError(f"report not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReportError(f"report is not valid JSON: {path}") from exc
    return report_from_dict(raw)


def report_to_dict(report: Report) -> dict[str, object]:
    return {
        "version": REPORT_VERSION,
        "target": report.target,
        "sha256": report.sha256,
        "tested_at": report.tested_at,
        "score": score(report.findings),
        "passed": report.passed,
        "findings": [
            {
                "id": finding.id,
                "title": finding.title,
                "severity": finding.severity,
                "category": finding.category,
                "blocks_solution": finding.blocks_solution,
                "present": finding.present,
                "evidence": finding.evidence,
            }
            for finding in report.findings
        ],
    }


def report_from_dict(raw: object) -> Report:
    if not isinstance(raw, dict):
        raise ReportError("report must be an object")
    if raw.get("version") != REPORT_VERSION:
        raise ReportError("unsupported report version")
    target = raw.get("target")
    digest = raw.get("sha256")
    tested_at = raw.get("tested_at")
    findings_raw = raw.get("findings")
    if not all(isinstance(value, str) and value for value in (target, digest, tested_at)):
        raise ReportError("report is missing target, sha256, or tested_at")
    if not isinstance(findings_raw, list):
        raise ReportError("report findings must be a list")
    return Report(
        target=target,
        sha256=digest,
        tested_at=tested_at,
        findings=[_finding_from_dict(item) for item in findings_raw],
    )


def _finding_from_dict(raw: object) -> Finding:
    if not isinstance(raw, dict):
        raise ReportError("each finding must be an object")
    try:
        severity = raw["severity"]
        blocks_solution = raw["blocks_solution"]
        present = raw["present"]
    except KeyError as exc:
        raise ReportError(f"finding is missing {exc.args[0]}") from exc
    if severity not in SEVERITY_WEIGHT:
        raise ReportError(f"finding severity is unknown: {severity}")
    if not isinstance(blocks_solution, bool) or not isinstance(present, bool):
        raise ReportError("finding blocks_solution and present must be booleans")
    try:
        return Finding(
            id=str(raw["id"]),
            title=str(raw["title"]),
            severity=str(severity),
            category=str(raw["category"]),
            blocks_solution=blocks_solution,
            present=present,
            evidence=str(raw.get("evidence", "")),
        )
    except KeyError as exc:
        raise ReportError(f"finding is missing {exc.args[0]}") from exc
