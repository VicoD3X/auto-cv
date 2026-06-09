# Auto-CV - Language Policy

## Core Rule

Auto-CV uses a deliberate split between repository language and product language.

```text
Repository layer -> English
Product layer    -> French
```

The repository is public and part of a professional GitHub presence. It should therefore remain clean, readable, and credible for an international technical audience.

The software itself is personal and built around a real French job application workflow. The product experience must therefore be French-first.

## English Layer

Use English for:

- README and repository presentation;
- badges and GitHub metadata;
- CI workflow names;
- package metadata;
- code identifiers;
- module names;
- technical architecture intended for external readers;
- changelog and contribution/security files.

## French Layer

Use French for:

- desktop UI labels;
- iPad companion UI labels;
- user-facing statuses;
- generated cover letter drafts;
- email draft content;
- local templates;
- workflow names shown in the app;
- onboarding/help text inside the app;
- validation messages shown in the app.

## Code Convention

Internal code stays in English for maintainability:

```text
ApplicationRecord.status = "ready"
```

User-facing rendering uses French:

```text
"ready" -> "Prêt à envoyer"
```

French strings should be centralized under:

```text
src/autocv/i18n/
```

This prevents UI text from being scattered across business logic.

## Default Locale

The default product locale is:

```text
fr-FR
```

The default repository/documentation presentation language is:

```text
en-US
```

Future support for English CVs or cover letters may exist per job application, but the software interface remains French-first.
