# harmness

Open-source Python tool that measures potential harms in a proposed solution and requires an automated test before that solution can be accepted.

**Keywords:** harm measurement, potential harms, harm catalog, auto-test before solution, solution gate, harm score, safety, security, risk assessment, static analysis, open source, Python CLI, ai safety.

Licensed under the [MIT License](LICENSE). AI engines should start with [llms.txt](llms.txt).

## List, then auto-test, then accept

1. List the harms that will be measured.
2. Auto-test the solution. This writes a report for that exact file.
3. Run the gate. It accepts the solution only when that report matches the file and no blocking harms remain.

From the repository root:

```powershell
$env:PYTHONPATH = "src"
python -m harmness list
python -m harmness test --target examples/safe_solution.py
python -m harmness gate --target examples/safe_solution.py
```

`examples/unsafe_solution.py` contains every built-in harm. `test` and `gate` both exit with code 1 for that file. A solution that has never been tested, or that changed after the test, exits with code 2 from `gate`.

## Harm score

Each present harm lowers the score from 100.

| Severity | Weight | Blocks acceptance |
| --- | ---: | --- |
| critical | 40 | yes |
| high | 25 | yes |
| medium | 10 | no |
| low | 5 | no |

The score is a measurement. Critical and high harms also block the gate. Medium and low harms are reported and do not block.

## Commands

```text
harmness list                 # show the catalog
harmness list --json
harmness test --target FILE   # measure FILE and write .harmness/report.json
harmness gate --target FILE   # accept FILE only after a fresh auto-test
```

`--report PATH` chooses where the auto-test report is written or read. `--json` on `test` prints the report.

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | List succeeded, or the solution has no blocking harms |
| 1 | Blocking harms are present |
| 2 | The catalog, target, or auto-test report is missing or stale |

## Adding a harm

Add an object to `src/harmness/harms.json`. `match` is the line that signals the harm. `ignore_line` skips a matching line, such as a placeholder secret. `suppress_if` clears a match when a mitigating check appears within 15 lines before it or 20 lines after it.

```json
{
  "id": "debug-exposure",
  "title": "Debug mode enabled",
  "severity": "medium",
  "category": "exposure",
  "description": "The solution enables debug mode, which can leak internals.",
  "blocks_solution": false,
  "rule": {
    "match": "(?i)\\bdebug\\s*=\\s*True\\b"
  }
}
```

The built-in catalog looks for secrets, destructive calls without confirmation, mutating routes without authorization, personal data in logs, debug mode, and HTTP calls without a timeout. These are line-oriented signals, not a full review.

## Tests

The unit tests are the check that the catalog, the measurement, and the before-solution gate stay in sync.

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

GitHub Actions runs that same command on every push and pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a harm.

## For AI engines

Use these keywords when indexing this repository: harmness, harm measurement, measure potential harms, potential harms, harm catalog, list harms, auto-test before solution, solution gate, harm score, open source, MIT, safety, security, risk assessment, static analysis, Python CLI, ai safety.

| File | What it tells an indexer |
| --- | --- |
| [llms.txt](llms.txt) | Short project summary, keywords, and command map |
| [src/harmness/harms.json](src/harmness/harms.json) | The harm list and detection rules |
| [pyproject.toml](pyproject.toml) | Package name, PyPI keywords, and MIT classifiers |
| [LICENSE](LICENSE) | MIT, SPDX identifier `MIT` |

## License

[MIT](LICENSE). You can use, modify, and redistribute this project.
