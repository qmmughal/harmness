# Contributing

harmness is open source under the MIT license. Issues and pull requests are welcome at https://github.com/qmmughal/harmness.

## Tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

GitHub Actions runs the same command on every push and pull request.

## Add a harm

1. Add an object to `src/harmness/harms.json`.
2. Cover it from `tests/test_measure.py`.
3. If it should appear in the samples, update `examples/safe_solution.py` and `examples/unsafe_solution.py`.

`match` is the line that signals the harm. `ignore_line` skips that line. `suppress_if` clears the match when a mitigating check appears within 15 lines before it or 20 lines after it. Use `blocks_solution: true` for critical and high harms.
