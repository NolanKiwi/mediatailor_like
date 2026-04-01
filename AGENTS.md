# Repository Guidelines

## Project Structure & Module Organization
This repository is currently a minimal scaffold. At the moment, the top level contains only this guide and an empty `.codex` placeholder file. When adding code, keep the layout predictable:

- `src/` for application code
- `tests/` for automated tests
- `assets/` for static files such as images or sample media
- `docs/` for design notes or operational runbooks

Use small, focused modules and group related files by feature or domain rather than by file type alone.

## Build, Test, and Development Commands
No build system or test runner is configured yet. Add project-level commands as soon as tooling is introduced and document them here and in the primary README.

Examples for a future setup:

- `npm install` to install JavaScript dependencies
- `npm test` to run the test suite
- `make build` to produce a distributable artifact

Prefer a single canonical command for each task so contributors do not have to guess.

## Coding Style & Naming Conventions
Match the conventions of the language introduced into the repository. Until a formatter is added, use consistent indentation and keep files readable:

- 2 spaces for YAML, JSON, and Markdown lists
- 4 spaces for Python
- `kebab-case` for Markdown and asset filenames
- `snake_case` or `camelCase` according to language norms

If you add tooling, prefer automated formatting and linting over manual enforcement.

## Testing Guidelines
Place tests under `tests/` and name them so their scope is obvious, for example `test_ingest.py` or `media-tailor.spec.ts`. Add fast unit tests first, then integration tests for external workflows. New features should ship with tests or a short note explaining why tests are not yet practical.

## Commit & Pull Request Guidelines
There is no git history in this workspace yet, so no established commit convention can be inferred. Start with short, imperative commit messages such as `Add media ingest parser`.

Pull requests should include:

- a brief description of the change
- linked issue or task reference when available
- test evidence or a note that no tests exist yet
- screenshots or sample output for UI or media changes
