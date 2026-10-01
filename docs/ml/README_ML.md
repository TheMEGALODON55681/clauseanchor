# ML setup

Owner: Tanishq Arya. Required Python: 3.12.

Run commands from the repository root. On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .\ml
.\.venv\Scripts\python.exe .\ml\scripts\check_contract.py
.\.venv\Scripts\python.exe -m unittest discover -s .\ml\tests -v
```

On Linux or macOS with Python 3.12 installed:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e ./ml
.venv/bin/python ml/scripts/check_contract.py
.venv/bin/python -m unittest discover -s ml/tests -v
```

Phase 1 uses the Python standard library at runtime. Setuptools is a packaging dependency. The 26 tests use `unittest`, so pytest is optional. Training dependencies will be isolated and pinned after compatibility checks in Phase 2.

`StubAnalyzer` only accepts the exact bundled fixture. Its outputs have `mode=stub`, `origin=fixture` and null confidence. This is an integration sample, not an inference model. See `Interface.md` for the boundary with Aryan's app.

All source offsets use Unicode code points with an exclusive end. Never normalize, strip or rewrap source text after computing its hash and offsets. `.gitattributes` preserves the fixture's bytes across Git checkouts.

Commit code, small fixtures, configs and measured summaries. Keep data, weights, indexes, checkpoints and credentials outside Git. Use `git check-ignore` before downloads and inspect staged paths before every commit.
