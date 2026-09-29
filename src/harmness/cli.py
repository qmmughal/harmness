import argparse
import json
import sys
from pathlib import Path

from harmness import __version__
from harmness.catalog import CatalogError, harm_to_dict, load_catalog
from harmness.measure import score
from harmness.models import Finding, Harm, Report
from harmness.report import ReportError, build_report, file_sha256, load_report, report_to_dict, save_report


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except CatalogError as exc:
        print(f"Harm catalog is invalid: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harmness",
        description="Measure potential harms and auto-test a solution before it can be accepted.",
    )
    parser.add_argument("--version", action="version", version=f"harmness {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    list_command = commands.add_parser("list", help="List potential harms")
    list_command.add_argument("--json", action="store_true", help="Print the catalog as JSON")
    list_command.set_defaults(handler=command_list)

    test_command = commands.add_parser("test", help="Auto-test a solution before it is accepted")
    test_command.add_argument("--target", required=True, help="Solution file to measure")
    test_command.add_argument("--report", help="Where to write the auto-test report")
    test_command.add_argument("--json", action="store_true", help="Print the report as JSON")
    test_command.set_defaults(handler=command_test)

    gate_command = commands.add_parser("gate", help="Accept a solution only after a fresh auto-test")
    gate_command.add_argument("--target", required=True, help="Solution file that was tested")
    gate_command.add_argument("--report", help="Auto-test report to read")
    gate_command.set_defaults(handler=command_gate)
    return parser


def command_list(args: argparse.Namespace) -> int:
    harms = load_catalog()
    if args.json:
        print(json.dumps({"version": 1, "harms": [harm_to_dict(harm) for harm in harms]}, indent=2))
    else:
        print(render_catalog(harms))
    return 0


def command_test(args: argparse.Namespace) -> int:
    target = Path(args.target)
    if not target.is_file():
        print(f"Target is not a file: {target}", file=sys.stderr)
        return 2
    report = build_report(target, target.read_text(encoding="utf-8", errors="replace"))
    report_path = _report_path(args.report)
    save_report(report, report_path)
    if args.json:
        print(json.dumps(report_to_dict(report), indent=2))
    else:
        print(render_measurement(report, report_path))
    return 0 if report.passed else 1


def command_gate(args: argparse.Namespace) -> int:
    target = Path(args.target)
    if not target.is_file():
        print(f"Target is not a file: {target}", file=sys.stderr)
        return 2
    report_path = _report_path(args.report)
    if not report_path.is_file():
        print(_missing_report_message(target, report_path))
        return 2
    try:
        report = load_report(report_path)
    except ReportError as exc:
        print(f"{exc}\nRun the auto-test again: harmness test --target {target}")
        return 2

    resolved = str(target.resolve())
    if report.target != resolved:
        print(_missing_report_message(target, report_path))
        return 2
    if report.sha256 != file_sha256(target):
        print(
            "The solution changed after the last auto-test.\n"
            f"Run harmness test --target {target} again before accepting it."
        )
        return 2
    fresh = build_report(target, target.read_text(encoding="utf-8", errors="replace"))
    print(render_gate(fresh))
    return 0 if fresh.passed else 1


def render_catalog(harms: list[Harm]) -> str:
    blocking = sum(1 for harm in harms if harm.blocks_solution)
    lines = [
        f"Potential harms ({len(harms)})",
        f"{blocking} block a solution until they are clear. Run harmness test before accepting one.",
        "",
    ]
    for harm in harms:
        gate = "blocks" if harm.blocks_solution else "notes"
        lines.append(f"[{harm.severity}] {harm.id} ({gate})")
        lines.append(f"  {harm.description}")
    return "\n".join(lines)


def render_measurement(report: Report, report_path: Path) -> str:
    lines = [
        f"Measured {len(report.findings)} potential harms in {report.target}",
        f"Harm score: {score(report.findings)}/100",
        "",
        *_finding_sections(report.findings),
        "",
    ]
    if report.passed:
        lines.append("No blocking harms. The auto-test is ready for the gate.")
    else:
        lines.append("Blocking harms are present. This solution cannot be accepted yet.")
    lines.append(f"Report written to {report_path}")
    lines.append(f"Next: harmness gate --target {report.target}")
    return "\n".join(lines)


def render_gate(report: Report) -> str:
    harm_score = score(report.findings)
    if report.passed:
        lines = [
            "Auto-test passed for this solution. No blocking harms.",
            f"Harm score: {harm_score}/100",
        ]
        noted = [finding for finding in report.findings if finding.present]
        if noted:
            lines.append("")
            lines.append("Noted (does not block):")
            lines.extend(_present_lines(noted))
        return "\n".join(lines)
    lines = [
        "Auto-test found blocking harms. This solution cannot be accepted.",
        f"Harm score: {harm_score}/100",
        "",
        *_present_lines(report.blocking),
    ]
    return "\n".join(lines)


def _finding_sections(findings: list[Finding]) -> list[str]:
    present = [finding for finding in findings if finding.present]
    clear = [finding for finding in findings if not finding.present]
    lines = ["Present"]
    if present:
        lines.extend(_present_lines(present))
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("Clear")
    if clear:
        lines.extend(f"  {finding.id}" for finding in clear)
    else:
        lines.append("  (none)")
    return lines


def _present_lines(findings: list[Finding]) -> list[str]:
    lines: list[str] = []
    for finding in findings:
        lines.append(f"  [{finding.severity}] {finding.id}")
        if finding.evidence:
            lines.append(f"    {finding.evidence}")
    return lines


def _report_path(raw: str | None) -> Path:
    if raw:
        return Path(raw)
    return Path.cwd() / ".harmness" / "report.json"


def _missing_report_message(target: Path, report_path: Path) -> str:
    return (
        "Auto-test required before this solution can be accepted.\n"
        f"No matching report at {report_path}.\n"
        f"Run: harmness test --target {target}"
    )

