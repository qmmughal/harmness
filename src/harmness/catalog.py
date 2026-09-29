import json
import re
from importlib.resources import files
from pathlib import Path

from harmness.models import Harm

SEVERITIES = ("critical", "high", "medium", "low")
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RULE_KEYS = {"match", "ignore_line", "suppress_if"}


class CatalogError(ValueError):
    """The harm catalog is missing a field or contains a rule that cannot be compiled."""


def default_catalog_path() -> Path:
    return Path(str(files("harmness").joinpath("harms.json")))


def load_catalog(path: Path | None = None) -> list[Harm]:
    catalog_path = path or default_catalog_path()
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CatalogError(f"catalog file not found: {catalog_path}") from exc
    except json.JSONDecodeError as exc:
        raise CatalogError(f"{catalog_path}: {exc}") from exc

    harms_raw = raw.get("harms") if isinstance(raw, dict) else None
    if not isinstance(harms_raw, list) or not harms_raw:
        raise CatalogError("catalog must contain a non-empty 'harms' list")

    harms = [compile_harm(item) for item in harms_raw]
    ids = [harm.id for harm in harms]
    duplicates = sorted({harm_id for harm_id in ids if ids.count(harm_id) > 1})
    if duplicates:
        raise CatalogError(f"duplicate harm ids: {', '.join(duplicates)}")
    return harms


def compile_harm(raw: object) -> Harm:
    if not isinstance(raw, dict):
        raise CatalogError("each harm must be an object")

    harm_id = _required_text(raw, "id")
    if not ID_PATTERN.fullmatch(harm_id):
        raise CatalogError(f"{harm_id!r} is not a lowercase hyphenated id")

    severity = _required_text(raw, "severity")
    if severity not in SEVERITIES:
        raise CatalogError(f"{harm_id}: severity must be one of {', '.join(SEVERITIES)}")

    blocks = raw.get("blocks_solution")
    if not isinstance(blocks, bool):
        raise CatalogError(f"{harm_id}: blocks_solution must be true or false")

    rule = raw.get("rule")
    if not isinstance(rule, dict):
        raise CatalogError(f"{harm_id}: rule must be an object")
    extra = set(rule) - RULE_KEYS
    if extra:
        raise CatalogError(f"{harm_id}: unknown rule fields: {', '.join(sorted(extra))}")

    return Harm(
        id=harm_id,
        title=_required_text(raw, "title"),
        severity=severity,
        category=_required_text(raw, "category"),
        description=_required_text(raw, "description"),
        blocks_solution=blocks,
        match=_compile_rule(harm_id, rule, "match"),
        ignore_line=_compile_optional(harm_id, rule, "ignore_line"),
        suppress_if=_compile_optional(harm_id, rule, "suppress_if"),
        rule={key: value for key, value in rule.items() if isinstance(value, str)},
    )


def harm_to_dict(harm: Harm) -> dict[str, object]:
    return {
        "id": harm.id,
        "title": harm.title,
        "severity": harm.severity,
        "category": harm.category,
        "description": harm.description,
        "blocks_solution": harm.blocks_solution,
        "rule": harm.rule,
    }


def _required_text(raw: dict, key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        harm_id = raw.get("id", "<unknown>")
        raise CatalogError(f"{harm_id}: {key} must be a non-empty string")
    return value.strip()


def _compile_rule(harm_id: str, rule: dict, key: str) -> re.Pattern[str]:
    value = rule.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{harm_id}: rule.{key} must be a non-empty string")
    return _compile(harm_id, key, value)


def _compile_optional(harm_id: str, rule: dict, key: str) -> re.Pattern[str] | None:
    value = rule.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"{harm_id}: rule.{key} must be a non-empty string when set")
    return _compile(harm_id, key, value)


def _compile(harm_id: str, key: str, pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise CatalogError(f"{harm_id}: rule.{key} is not a valid regex: {exc}") from exc
