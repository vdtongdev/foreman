# Fix Foreman hook commands on Windows

## Goal

Keep the existing POSIX hook commands and add Windows-specific commands that run under Windows PowerShell 5.1. Preserve fail-open behavior for every hook.

## Evidence

The installed `SessionStart` command ends in `|| true`. Running that command in Windows PowerShell 5.1 exits 1 during parsing, before `uv` or the Python hook starts. Running the installed Python hook directly exits 0.

## Tasks

### 1. Add a regression test

- **Agent:** implementer
- **Files:** `tests/test_dispatch.py`
- Assert every registered command has a `commandWindows` override and a 30-second timeout.
- Assert the Windows override uses PowerShell-compatible environment variable syntax to resolve the plugin root, invokes the same registered hook, and does not use the POSIX `|| true` suffix.
- Assert the Windows override retains fail-open behavior when the launcher or hook exits nonzero.
- Run the focused dispatch test and confirm the new assertion fails against the current manifest.

### 2. Add Windows-specific hook commands

- **Agent:** implementer
- **Plan:** `docs/plans/2026-10-28-windows-hook-launcher.md`
- **Files:** `hooks/hooks.json`
- Add a `commandWindows` value to every hook handler. Use a PowerShell-safe plugin-root reference and preserve the existing POSIX `command` values unchanged.
- Ensure launcher failures still exit 0, matching the existing fail-open contract.

### 3. Verify

- **Agent:** verifier
- Run `uv run --with pytest pytest -q tests/test_dispatch.py` and the full suite.
- Execute the Windows `SessionStart` override under Windows PowerShell 5.1 with the installed plugin root; require exit code 0 and valid SessionStart JSON.
- Review the diff to confirm unrelated worktree changes are untouched.
