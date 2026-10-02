# RUNE Core

RUNE is a persistent personal intelligence runtime.

It is not a single-device assistant. RUNE's intelligence is designed to persist independently of the interfaces and environments through which it is accessed.

## Core loop

understand -> remember -> retrieve -> reason -> decide -> act with permission -> observe -> verify -> learn

## Current architecture

- Kernel: identity, events, runtime state, working memory, agency and verification
- Persistence: SQLite event journal for the local-first runtime
- Context: bounded working context assembled from memory and external evidence
- Model boundary: ModelProvider, keeping RUNE independent of any single model
- Local inference: optional Ollama adapter
- Retrieval boundary: provider-neutral retriever interface
- Runtime: composition layer for local persistent operation
- CLI: first human-facing runtime interface

## Local-first principle

RUNE can run locally while still using the internet for fresh information. The local model is a replaceable reasoning/language component, not the whole intelligence architecture.

## Engineering invariants

1. Intent is not a decision.
2. A decision is not an attempt.
3. An attempt is not a successful outcome.
4. An outcome is not verified until evidence confirms it.
5. No world-changing action occurs without appropriate authority.
6. Unknown capability is never treated as completed capability.
7. Feasibility and constraints are evaluated before execution.

## Status

Milestone 0.2: Persistent local runtime + model/retrieval boundaries.


## Brand system

RUNE's visual identity is now locked to the geometric interlocked RUNE glyph, a dark near-black interface with green signal accents, **Manrope** for human-facing UI, and **DM Mono** for system/telemetry surfaces.

Brand assets live under `brand/`, with the production glyph exposed at `frontend/public/rune-glyph.svg`. The shell, app icon/favion and RUNE Island use the same mark so the identity persists across surfaces.

The visual system is intentionally not a generic fantasy-rune aesthetic. The glyph is the persistent system identity; the interface may evolve around it.
