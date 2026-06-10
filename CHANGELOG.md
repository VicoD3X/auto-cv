# Changelog

## Unreleased

- Parked the previous local AI integration path on `vicod3x/ai-parking` for later reactivation.
- Added safe document edit sessions: duplicate DOCX/PDF files into `Result`, open the copy, finalize, or cancel without touching source files.
- Added a `Pre-suppression` view backed by `Result/_PreSuppression` to restore or permanently delete canceled/unchanged work copies, with automatic purge after 30 days.
- Added per-target result folders using `Result/<Target>_<RoleOrMission>_<Date>/`.
- Added a simple document pack action for applications and freelance opportunities.
- Recentered the V1 UI on deterministic document preparation, local copies, local conversion, and manual validation.
- Reworked GitHub into a public project library with copy-name, copy-URL, Word hyperlink copy, and open-project actions.
- Added direct open actions for generated CV, letter/proposal, mail, target folder, and Result.
- Added local user-facing logs at `~/.autocv/logs/autocv.log`.

## 0.2.0 - V1 Development Start

- Added a Windows desktop launcher and Auto-CV icon.
- Added the first PySide6 operational dashboard UI.
- Added V1 domain entities for job offers, freelance opportunities, and application records.
- Added local SQLite initialization and repositories.
- Added workspace bootstrap with source document validation.
- Added V1 use cases for creating job and freelance drafts from generic documents.
- Added local result directory, smart document naming, and mail draft contracts.
- Added Qwen3-14B Q4_K_M local AI profile with Q5_K_M quality option.
- Added V1 public AI service hooks for letter/proposal adaptation and mail drafting.
- Added tests for the V1 data foundation.

## 0.1.0 - Foundation

- Defined Auto-CV as a personal local-first Windows PC application.
- Added iPad companion architecture through an optional private remote layer.
- Added public repository documentation foundation.
- Added initial Python project skeleton.
- Added CI workflow for linting and tests.
