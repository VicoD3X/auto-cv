# Auto-CV - Architecture

## Decision

Auto-CV is a personal, local-first software project.

The target platforms are:

- **Windows PC**: main application, data source of truth, local storage, local AI, document generation.
- **iPad**: companion access to the PC workspace when the PC is online and reachable.

macOS is not a target for now.

## Language Boundary

Auto-CV has two language layers:

- repository and technical presentation: **English**;
- software experience and generated user content: **French**.

This means the codebase can keep English identifiers while every user-facing label, workflow status, generated draft, and template defaults to French.

French product strings should be centralized under `src/autocv/i18n/`.

## Public / Private Boundary

The public repository contains the project shell:

- documentation;
- product architecture;
- UI direction;
- public contracts;
- safe placeholder adapters;
- tests and CI.

The real engine can remain private for now. This includes:

- local prompts;
- personal scoring rules;
- model experiments;
- private automation logic;
- sensitive workflow heuristics;
- Gmail or document automation details that should not be exposed yet.

The public app should depend on contracts, not directly on private implementation details.

```text
public repo
  -> src/autocv/engine/contracts.py
  -> src/autocv/engine/public_stub.py
  -> src/autocv/engine/loader.py

ignored local code
  -> src/autocv_private_engine/
  -> private_engine/
```

If the private engine is absent, the app must still start and use the public stub.

## Source Documents

The V1 uses one local source folder for professional documents:

```text
%USERPROFILE%\Desktop\GENERIQUE PRO
```

Expected files:

```text
CV_Victor_Aubry_Data_Scientist_pdf.pdf
Lettre_motivation_Victor_Aubry.docx
```

The CV is treated as a stable generic document for V1. No AI modification is planned for the CV.

The cover letter is treated as the editable generic base. The private local engine can adapt it lightly to a specific job offer or freelance mission.

The document contents and generated exports must stay outside the public repository.

## Result Directory

All generated, sorted, renamed, or prepared documents must be written to:

```text
%USERPROFILE%\Desktop\GENERIQUE PRO\Auto-CV\Result
```

The app should create this directory during workspace bootstrap.

This folder is local-only and must not be committed to Git.

## Smart Document Naming

Generated documents should use stable explicit names:

```text
TypeDocument_TargetName_RoleOrMission_Date.ext
```

Examples:

```text
CV_Airbus_Data_Scientist_2026_06_09.pdf
Lettre_Motivation_Airbus_Data_Scientist_2026_06_09.docx
Proposition_Freelance_Client_Dashboard_2026_06_09.docx
Mail_Airbus_Data_Scientist_2026_06_09.txt
```

The public repository owns the naming contract. The private engine can propose smarter labels later, but the generated names must remain readable and Windows-safe.

## GitHub Project Context

Auto-CV should sync selected GitHub project metadata and content locally so the private engine can reuse real project evidence when adapting cover letters.

The sync layer should collect safe project context such as:

- repository name;
- description;
- topics;
- languages;
- README summary;
- selected project highlights;
- local notes added manually.

The AI layer should use this context to ground letter adjustments in real projects, without inventing experience.

## Mail Drafting

The V1 can delegate mail drafting to the private local AI engine:

- email subject;
- email body;
- short attachment reminder;
- salary application tone;
- freelance proposal tone.

The public repository exposes the mail draft contract. The private engine owns the prompt and generation details.

## Document Format Conversion

The V1 includes a document conversion layer for:

- DOCX;
- PDF;
- XLSX.

Priority conversions:

```text
DOCX -> PDF
PDF  -> DOCX
XLSX -> PDF
PDF  -> XLSX
```

DOCX -> PDF and XLSX -> PDF are export workflows. PDF -> DOCX and PDF -> XLSX are reconstruction workflows and should be treated as best-effort operations.

The public repository can expose conversion contracts. The private local engine or local adapters perform the actual conversion.

The public repository can expose sync contracts and cache structure. The private engine decides how to rank and inject project context.

## Architecture Shape

Auto-CV should be built as a **PC-first desktop application with an optional private remote layer**.

The PC app must remain fully usable offline. The remote layer only exists to expose selected features to the iPad when the PC is running.

```text
Windows PC
  |
  +-- Desktop UI
  |
  +-- Application use cases
  |
  +-- Domain model
  |
  +-- Local infrastructure
  |     +-- SQLite database
  |     +-- document folders
  |     +-- local cache
  |     +-- local logs
  |
  +-- Local AI engine
  |
  +-- Optional private remote server
        |
        +-- iPad companion access
```

The iPad experience is a companion surface, not the main product. The cleanest zero-cost option is a lightweight local/private HTTP interface served by the PC and opened from the iPad over LAN or a private tunnel.

## Modes

### Offline Mode

Offline mode is the default. It must support:

- opening the PC application;
- reading local data;
- creating and editing application records;
- preparing CV and cover letter drafts;
- exporting local files;
- queuing actions that require connectivity.

### Semi-Local Online Mode

This mode is active when the PC is on and exposes a private remote service.

It can support:

- iPad access to the local workspace;
- remote review of offers and drafts;
- remote validation of generated documents;
- triggering exports or queued actions from the iPad.

The PC disk remains the storage backend.

### Internet-Dependent Mode

This mode is optional and only used for integrations such as:

- Gmail draft creation or sending;
- external job offer retrieval;
- model downloads;
- update checks.

No critical workflow should depend on this mode.

## Proposed Stack

### Core

- Python 3.13
- PySide6 / Qt for the Windows desktop UI
- SQLite for local data
- SQLAlchemy or SQLModel for persistence
- Pydantic for schemas

### Remote iPad Layer

- FastAPI for the private local server
- Uvicorn for serving it from the PC
- Authentication token stored locally
- LAN access first
- Private tunnel later if needed

### AI Layer

The AI engine should be adapter-based:

```text
AiService
  +-- local_llm_service
  +-- rules_service
  +-- hybrid_service
```

This avoids locking the project to one model too early. Gemma, DeepSeek, or other local models can be benchmarked later through a local runner such as Ollama or llama.cpp.

## Data Storage

Recommended local storage layout:

```text
Auto-CV data directory
  autocv.sqlite
  documents/
    cv/
    cover_letters/
    job_offers/
    exports/
  cache/
  logs/
```

The database stores structured records. Files stay in dedicated folders and are referenced by stable IDs.

## Code Layout

```text
src/autocv/
  app/              # startup and orchestration
  ai/               # local AI adapters and generation helpers
  documents/        # document import, export, and attachment bundles
  domain/           # pure business entities
  engine/           # public engine contracts and safe stub
  infrastructure/   # database, filesystem, network adapters
  mail/             # Gmail integration and email drafts
  projects/         # GitHub project sync contracts and project context
  remote/           # private server for iPad companion access
  settings/         # local configuration and paths
  sync/             # queue, status, online/offline transitions
  conversion/       # document format conversion contracts and safe stub
  ui/               # Windows desktop UI
  use_cases/        # application workflows
```

## Security Principles

Auto-CV will manipulate sensitive personal data: CVs, cover letters, emails, job history, and possibly Gmail credentials.

The project should therefore follow these rules from the start:

- no secrets committed to Git;
- no private engine code committed to Git for now;
- Gmail credentials stored outside the repository;
- local tokens excluded by `.gitignore`;
- remote iPad access protected by a local token;
- no public exposure of the PC server by default;
- logs should never contain full email tokens or full generated letters.

## Current Foundation

The current foundation is:

**Windows PC desktop app, local-first storage, optional private iPad companion layer, zero-cost infrastructure, public repository polish.**
