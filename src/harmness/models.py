from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Harm:
    id: str
    title: str
    severity: str
    category: str
    description: str
    blocks_solution: bool
    match: re.Pattern[str]
    ignore_line: re.Pattern[str] | None
    suppress_if: re.Pattern[str] | None
    rule: dict[str, str]


@dataclass(frozen=True)
class Finding:
    id: str
    title: str
    severity: str
    category: str
    blocks_solution: bool
    present: bool
    evidence: str


@dataclass(frozen=True)
class Report:
    target: str
    sha256: str
    tested_at: str
    findings: list[Finding]

    @property
    def blocking(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.present and finding.blocks_solution]

    @property
    def passed(self) -> bool:
        return not self.blocking
