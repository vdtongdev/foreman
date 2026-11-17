# Install CodeGraph in this repository

## Goal

Initialize CodeGraph in the Foreman repository and build its local index.

## Task

- Agent: drafter
- Run `codegraph init` from the repository root.
- Keep changes limited to repository-local CodeGraph setup; do not run `codegraph install`, which changes agent-wide configuration.

## Acceptance

- A `.codegraph/` directory exists at the repository root and contains the generated index.
- `codegraph status` reports the repository index as initialized.
- The agent-wide configuration is unchanged.

## Verification

- Agent: verifier
- Inspect the resulting repository status and run `codegraph status`.
