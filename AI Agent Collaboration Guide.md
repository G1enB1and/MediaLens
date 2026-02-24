
# AI Agent Collaboration Guide for Antigravity

### From Gemini

This document defines the protocols, standards, and file locations for AI agents (like Antigravity and Codex CLI) working in the MediaManagerX repository. Following these guides ensures consistency and prevents redundant or conflicting work.

## 1. Core Instruction Files (Source of Truth)

All agents MUST read and adhere to these documents before proposing or implementing changes:
- **[MASTER_BRIEF.md](file:///c:/My_Projects/MediaManagerX/MediaManagerX/MASTER_BRIEF.md)**: High-level purpose, non-negotiables, and architecture guardrails.
- **[PHASE1_PLAN.md](file:///c:/My_Projects/MediaManagerX/MediaManagerX/PHASE1_PLAN.md)**: Specific MVP goals, UX rules, and the current build sequence.
- **[DECISIONS.md](file:///c:/My_Projects/MediaManagerX/MediaManagerX/DECISIONS.md)**: Locked technical choices (frameworks, storage models, etc.).
- **[README.md](file:///c:/My_Projects/MediaManagerX/MediaManagerX/README.md)**: Repo layout and local development setup.
## 2. Progress and Coordination Files

To avoid stepping on each other's toes, agents should track their work using the following lifecycle.
### File Types

1. **Task List (`task.md`)**: A living checklist of current objectives and status.
2. **Implementation Plan (`implementation_plan.md`)**: A detailed technical proposal drafted for user approval *before* significant execution.
3. **Walkthrough (`walkthrough.md`)**: A summary of completed work, including verification results and links to changes.
### Where to Look for Progress Files

Agents may store these files in different locations depending on their configuration:

- **Root Directory**: Some agents (e.g., Codex CLI) may write these directly to the repository root.
- **Antigravity Internal Storage**: Antigravity stores session-specific files in `.gemini/antigravity/brain/<session-id>/`.

**Always check both the root and the `.gemini/` folder (recursively for recent activity) to synchronize with other agents before starting a new task.**

## 3. Communication Standards

- **Proactive Updates**: If you start a new task, create/update a `task.md`.
- **User Review**: Always request review for an `implementation_plan.md` before making architecture-level changes.
- **Verification**: Never consider a task done without a `walkthrough.md` documenting manual or automated verification success.


---

Everything above is from the point of view of Gemini 3 Flash within Antigravity.
Next step is to ask Codex CLI What it uses for itself in projects like this.

---

*Last updated: 2026-02-22*