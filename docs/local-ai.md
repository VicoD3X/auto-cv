# Auto-CV - Local AI

## Current V1 Position

Local AI is **disabled for the reliability-first V1**.

The desktop app must remain usable without loading a local model. The V1 uses deterministic workflows for document copying, naming, tracking, conversion, GitHub context display, and mail draft preparation.

The local AI layer remains documented as an optional future/experimental capability behind an explicit setting.

## Model Choice

The deferred local AI profile targets:

```text
Qwen3-14B GGUF
Default quantization: Q4_K_M
Quality option:       Q5_K_M
Runner:               llama.cpp
```

The default starts with `Q4_K_M` because local execution must be validated before chasing higher quality. `Q5_K_M` remains the quality option if local performance is comfortable.

## Public / Private Split

The public repository contains:

- model profile;
- runner contract;
- safe public stub;
- task boundaries;
- documentation.

The private engine contains:

- prompts;
- local runner implementation;
- document adaptation logic;
- mail generation logic;
- project-context selection rules.

## Deferred AI Tasks

Qwen3-14B may later be used for:

- adapting the generic cover letter to a job offer;
- drafting a short freelance proposal;
- preparing an email subject;
- preparing an email body;
- using synchronized GitHub project context as evidence.

When re-enabled, the desktop UI can call these tasks through the public `V1AiService`:

```text
Adapter la lettre -> cover_letter_adaptation or freelance_proposal
Préparer le mail -> mail_draft
```

In the reliability-first V1, the app does not require the private engine and does not start the local model by default.

Qwen3-14B is not used for:

- modifying the CV content;
- sending emails automatically;
- inventing experience;
- fully autonomous application decisions.

## Runner

The preferred runner is `llama.cpp` with an OpenAI-compatible local endpoint:

```text
http://127.0.0.1:8080/v1
```

Reference model:

```text
Qwen/Qwen3-14B-GGUF:Q4_K_M
```

Quality switch:

```text
Qwen/Qwen3-14B-GGUF:Q5_K_M
```

Typical local server command:

```powershell
llama-server -hf Qwen/Qwen3-14B-GGUF:Q4_K_M
```

## Generation Defaults

For V1 writing tasks:

- thinking mode disabled by default;
- concise French output;
- human validation required;
- no CV modification;
- no personal document content committed to Git.

The private engine may expose a manual switch to Q5_K_M after Q4_K_M is validated on the machine.

## Private Local Package

The local private package is expected at:

```text
src/autocv_private_engine/
```

This folder is ignored by Git. It contains the actual local runner, private prompts, and Qwen3 request handling.
