# Auto-CV - Private Engine Boundary

## Rule

The repository is public. The real engine is private for now.

The public repository should expose enough structure to show the product direction and engineering quality, but it should not publish the internal engine logic before it is ready.

## Public Repository

The public repository can contain:

- architecture and product documentation;
- UI shell;
- data model;
- public engine contracts;
- safe placeholder engine implementation;
- tests and CI;
- examples without personal data.

## Private Engine

The private engine should contain:

- local prompts;
- personal matching rules;
- ranking and scoring heuristics;
- local LLM experiments;
- workflow automation details;
- private document conversion adapters and reconstruction rules;
- sensitive Gmail/document automation;
- any logic that would reveal too much about the internal process.

## Ignored Locations

The following locations are ignored by Git:

```text
private/
private_engine/
local_engine/
engine_private/
src/autocv_private/
src/autocv_private_engine/
```

## Integration Contract

The public app imports an engine through a loader.

If a private engine package named `autocv_private_engine` exists locally, the loader can use it.
If it does not exist, the app falls back to a public stub.

This keeps the repository runnable without publishing the real engine.
