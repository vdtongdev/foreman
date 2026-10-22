import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


def run_hook(name, payload, env=None):
    import json
    import os
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "foreman_hooks.py"), name],
        input=stdin, capture_output=True, text=True,
        env={**{k: v for k, v in os.environ.items() if k not in ("CLAUDE_PLUGIN_DATA", "FOREMAN_SOLO")},
             **(env or {})},
    )
    return r.stdout, r.stderr, r.returncode
