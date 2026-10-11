# Independent Audit — ugc-marketplace

**Auditor:** orchestrator subagent (adversarial verification pass)
**Date:** 2026-10-11
**Scope:** dependency, security, Python-version, test-integrity, dead/duplicate code.
Environment: repo venv `.venv/bin/python` = **Python 3.12.14**; system `python3` = **Python 3.9.6**.

---

## 1. Dependency audit

```text
$ ./.venv/bin/pip list --outdated 2>&1 | head -20
[exit=0]                # <- no packages listed
```
**Outdated packages: 0.** Network confirmed live; result genuine.

Constraints: `requirements.txt` and `pyproject.toml` use unbounded `>=` throughout (e.g. `fastapi>=0.115.0`, `scikit-learn>=1.4.0`). No `>=0.0` wildcards.

**Divergence between dependency sources:** `pyproject.toml` declares `urllib3[asyncio]`-adjacent `langchain-core`, `langchain-openai`, `deepagents`, `redis`, `asyncpg`, `aiokafka`, `orjson`, `psycopg2-binary` that are **not in `requirements.txt`**; conversely `requirements.txt` lists `numpy`, `scikit-learn`, `passlib[bcrypt]`, `slowapi`, `bleach` not in `pyproject.toml`. `urllib3`/`requests` appear **only** in `pyproject.toml` (0 hits in `requirements.txt`). The installed venv does contain `urllib3`/`requests` as transitive deps, masking the divergence.

## 2. Security scan

`bandit` not installed in this venv (`No module named bandit`; listed in `requirements-dev.txt` but dev extras were never installed). Ran analyzer from gated-communities venv (bandit 1.9.4) over `app` + `src`:
```text
$ gated-communities/.venv/bin/python -m bandit -r ugc-marketplace/app ugc-marketplace/src -ll
Run metrics:
        Total issues (by severity):
                Low: 263
                Medium: 0
                High: 0
Files skipped (0):
```
**MEDIUM+ findings: 0.** Note bandit emitted many `nosec encountered (B108/B608), but no failed test on file …` warnings — the `# nosec` comments in `app/database.py` and `src/ugc_marketplace/database/archival.py` are attached where the flagged test does not fire, so they are decorative, not suppressing real findings.

## 3. Python-version compatibility

- Declared: `requires-python = ">=3.11"`; CI matrix `["3.11","3.12"]` — **correct**, tests the floor.
- **One committed source file is syntactically invalid on every Python version, including the declared floor and 3.12 (verified):**
```text
$ .venv/bin/python -c "compile(open('src/ugc_marketplace/api/payments.py').read(),'p','exec')"
File "p.py", line 5
    from __future__ import annotations
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
SyntaxError: from __future__ imports must occur at the beginning of the file
```
Cause — file starts with a stray import **before** the docstring/`__future__`:
```text
1: from datetime import timezone
3: """Payment API endpoints for UGC Marketplace."""
5: from __future__ import annotations
```
`from __future__` imports must be the first statement (after the docstring). This is **not** a version mismatch (my 3.9.6 grammar check flagged the same file, and 3.12 rejects it too) — it is a broken module. `ast.parse()` happens to accept it, so bandit did **not** skip the file and reported 0 — a false-clean signal.

**Verdict: version declaration correct; `api/payments.py` is broken.**

## 4. Test-suite integrity

```text
$ .venv/bin/python -m pytest tests -p no:cacheprovider
873 passed, 65 warnings in 71.67s (0:01:11)
```
**REAL tail line: `873 passed`** — the suite is **green**.

> *Method note (adversarial):* the summary line is absent if you also pass `-q` on the CLI, because the repo's `pyproject.toml` already sets `addopts = "-q"`; doubling it (`-qq` effective) makes pytest suppress the count line. This is standard pytest behaviour, **not** a repo defect — but it does mean a casual `pytest -q` prints no total, which is exactly how a reader can be misled. Run without the extra `-q` to see the real count.

**Green suite masks a non-startable app.** The test suite never imports the application's router wiring, so the payments breakage is invisible to it:
```text
$ (cd src && ../.venv/bin/python -c "import ugc_marketplace.main")
  File ".../src/ugc_marketplace/api/payments.py", line 5
    from __future__ import annotations
SyntaxError: from __future__ imports must occur at the beginning of the file
```
Import chain: `ugc_marketplace/main.py:24` → `ugc_marketplace.api.routes` → `ugc_marketplace/api/routes.py:11` → `ugc_marketplace.api.payments` → SyntaxError. Also `src/ugc_marketplace/api/routers.py:9` imports it. **The application cannot start, yet 873 tests pass.**

Deleted-tests signal: `.restore/` holds backups of previously-removed tests (`test_dashboard.py`, `test_content_workflow.py`, `unit/test_{transaction,creator}_service_unit.py`, `unit/test_fraud_detection_unit.py`, `test_middleware/test_error_handler.py`). All are **now PRESENT** under `tests/` (commit `6fd25b3` "restore deleted coverage"). No live quarantine — `.restore/` itself is redundant now.

## 5. Dead / duplicate code signal

**Largest source files with ZERO test references** (grep of module name across `tests/` → 0 hits each):
| file | lines | tests refs |
|---|---|---|
| src/ugc_marketplace/agents/_content_marketplace.py | 1143 | 0 |
| src/ugc_marketplace/agents/_community_curation.py | 724 | 0 |
| src/ugc_marketplace/agents/_quality_scoring.py | 688 | 0 |
| src/ugc_marketplace/services/listing_service.py | 602 | 0 |
| src/ugc_marketplace/services/payment_service.py | 545 | 0 |
≈ **3,700 lines** of the biggest agent/service modules are not referenced by any test.

Also present: a **tests directory inside the shipped package** — `src/ugc_marketplace/tests/test_agents/test_rights_management.py` (1264 lines) lives under `src/`, not `tests/`. Packaging includes `[tool.hatch.build.targets.wheel] packages = ["src/ugc_marketplace","app"]`, so this test file is **shipped in the wheel**.

---

## Top 3 REAL issues (ranked)

1. **[VERIFIED DEFECT — CRITICAL] `src/ugc_marketplace/api/payments.py` has a runtime SyntaxError** (`from __future__` placed after another import, line 5). It is imported by `api/routes.py` and `api/routers.py`, so **`import ugc_marketplace.main` fails — the app cannot start.** bandit and `ast.parse` silently tolerate it (false-clean).
2. **[VERIFIED DEFECT — HIGH] Green test suite gives false assurance.** `873 passed`, but the suite never exercises the app router wiring (`main.py` → `routes.py` → `payments.py`), which is exactly where the fatal import lives. A 100 %-green run coexists with an un-startable application.
3. **[VERIFIED DEFECT — MEDIUM] Large untested surface + shipped test code.** ~3,700 lines across the five largest agent/service modules have zero test references; a 1264-line test file is bundled inside the distributed `ugc_marketplace` package.

### Minimal, verifiable fix (one per repo) — `docs/AUDIT-orchestrator.patch`
Moves the stray `from datetime import timezone` below the `from __future__ import annotations` line in `api/payments.py`:
```text
$ git -C ugc-marketplace apply --check docs/AUDIT-orchestrator.patch
[exit=0]
```
> This is a **patch artifact only** — no `src/**`, `tests/**`, or `.github/**` file was modified by this audit (out of scope). Verify after applying with:
> `(cd src && .venv/bin/python -c "import ugc_marketplace.main; print('app imports OK')")`.
