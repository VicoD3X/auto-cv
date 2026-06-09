# Auto-CV

![Status](https://img.shields.io/badge/status-concept%20foundation-blue)
![Python](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows%20PC%20%2B%20iPad-24292f)
![Mode](https://img.shields.io/badge/mode-local--first-success)
![UI Language](https://img.shields.io/badge/UI-fr--FR-0055A4)
![CI](https://github.com/VicoD3X/auto-cv/actions/workflows/ci.yml/badge.svg)

Auto-CV is a personal desktop-first tool designed to remove the friction from job applications:
CV variants, cover letters, job offers, attachments, exports, and optional Gmail sending in one clean workspace.

The repository is intentionally public and polished, while the software remains a personal internal tool.

## Language Boundary

Auto-CV has a deliberate language split:

- **Repository presentation**: English for README, badges, CI, code identifiers, package metadata, and public-facing technical polish.
- **Product experience**: French for the software UI, user-facing labels, generated workflow content, application statuses, templates, and local personal workspace.

This keeps the GitHub repository clean and internationally readable while preserving the actual tool as a French personal productivity app.

## Product Direction

Auto-CV is not a commercial SaaS and not a web app.

The core application runs locally on a Windows PC. When the PC is on, it can expose a lightweight private remote layer so an iPad can access the same local workspace. The PC remains the source of truth: data, documents, local AI, and application history live on the PC disk.

```text
Windows PC app
  -> local database
  -> local document storage
  -> local AI / automation engine
  -> optional private remote server
       -> iPad companion access
```

## Problem

Applying for jobs often means juggling too many moving parts:

- multiple CV versions;
- cover letter rewrites;
- job offer notes;
- file explorer back-and-forth;
- attachment preparation;
- email drafts and sent applications;
- repeated context switching.

Auto-CV centralizes that workflow so the application process becomes easier to start, easier to track, and less mentally draining.

## Target Scope

The first useful version should help with:

- managing reusable CV and cover letter versions;
- storing job offers and company context;
- generating tailored application drafts;
- exporting the right document bundle;
- tracking application status;
- optionally preparing or sending Gmail messages with attachments.

The long-term engine can combine deterministic rules, templates, local machine learning, and a local open-source LLM runner.

## Technical Foundation

- Python for the application core, automation, AI workflows, and data processing.
- PySide6 / Qt for the Windows desktop interface.
- SQLite for local-first storage.
- Pydantic for typed schemas.
- SQLAlchemy or SQLModel for persistence.
- FastAPI as an optional private remote layer for iPad access.
- Local AI through a pluggable adapter, with models benchmarked later.

## Repository

```text
docs/
  architecture.md
  concept.md
  data-model.md
  language-policy.md
  roadmap.md
src/autocv/
  app/
  ai/
  documents/
  domain/
  infrastructure/
  i18n/
  mail/
  remote/
  settings/
  sync/
  ui/
  use_cases/
tests/
```

## Local Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m autocv.app.main
```

## Checks

```powershell
pytest
ruff check .
```

## License

No open-source license has been selected yet. Until a license is added, all rights are reserved by default.
