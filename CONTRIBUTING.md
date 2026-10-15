# Contributing to Clawforge

## Development Setup

1. Clone the repository
2. Install dependencies via the committed lockfile
3. Copy `.env.example` to `.env` and fill in required values
4. Run the test suite: `pytest tests/ -v`

## Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation only
- `test:` — adding or fixing tests
- `refactor:` — code change that neither fixes a bug nor adds a feature
- `chore:` — tooling, deps, config
- `ci:` — CI/CD changes
- `build:` — build system or dependency changes

## Pull Request Checklist

- [ ] New code has tests in the same commit
- [ ] `ruff check .` passes
- [ ] `mypy src/` passes
- [ ] `pytest --cov=clawforge` meets the 60% floor
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] No secrets or credentials committed

## Test Discipline

Each commit that changes behavior should include the tests that prove it.
Large mixed commits (refactor + feature + formatting) are discouraged — split
them into focused commits per module.

