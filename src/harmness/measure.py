from harmness.catalog import load_catalog
from harmness.models import Finding, Harm

WINDOW_BEFORE = 15
WINDOW_AFTER = 20
EVIDENCE_LIMIT = 3
SNIPPET_LIMIT = 120

SEVERITY_WEIGHT = {
    "critical": 40,
    "high": 25,
    "medium": 10,
    "low": 5,
}


def measure(text: str, harms: list[Harm] | None = None) -> list[Finding]:
    catalog = harms if harms is not None else load_catalog()
    return [evaluate(harm, text) for harm in catalog]


def evaluate(harm: Harm, text: str) -> Finding:
    evidence = collect_evidence(harm, text)
    return Finding(
        id=harm.id,
        title=harm.title,
        severity=harm.severity,
        category=harm.category,
        blocks_solution=harm.blocks_solution,
        present=bool(evidence),
        evidence=evidence,
    )


def collect_evidence(harm: Harm, text: str) -> str:
    lines = text.splitlines()
    hits: list[str] = []
    for index, line in enumerate(lines):
        if harm.ignore_line and harm.ignore_line.search(line):
            continue
        if not harm.match.search(line):
            continue
        if harm.suppress_if is not None and harm.suppress_if.search(_window(lines, index)):
            continue
        snippet = line.strip()
        if len(snippet) > SNIPPET_LIMIT:
            snippet = snippet[: SNIPPET_LIMIT - 3] + "..."
        hits.append(f"line {index + 1}: {snippet}")
        if len(hits) == EVIDENCE_LIMIT:
            break
    return "; ".join(hits)


def score(findings: list[Finding]) -> int:
    penalty = sum(SEVERITY_WEIGHT[finding.severity] for finding in findings if finding.present)
    return max(0, 100 - penalty)


def _window(lines: list[str], index: int) -> str:
    start = max(0, index - WINDOW_BEFORE)
    end = min(len(lines), index + WINDOW_AFTER + 1)
    return "\n".join(lines[start:end])
