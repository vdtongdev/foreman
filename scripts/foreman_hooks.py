# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Foreman hook dispatcher. Every hook fails open: errors go to stderr, exit 0."""
import json
import sys
import traceback

HOOKS = {"guard": lambda p: None}  # Task 4 replaces the placeholder


def main(argv):
    try:
        payload = json.loads(sys.stdin.read())
        result = HOOKS[argv[1]](payload)
        if result is not None:
            print(json.dumps(result))
    except BaseException:
        traceback.print_exc()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
