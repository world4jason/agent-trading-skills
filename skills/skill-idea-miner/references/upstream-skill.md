---
name: skill-idea-miner
description: Mine user-selected Codex conversations or session exports for trading-skill ideas, score novelty, feasibility and trading value, and maintain a prioritized backlog. Use for a requested trading-skill backlog refresh or idea review.
---

## Codex execution

Before running this skill, read [Codex runtime](/Users/world4jason/.codex/skill-bundles/codex-trading-skills/CODEX_RUNTIME.md). It defines this installation's interpreter, resource paths, available-tool mapping, and external prerequisites.


# Skill Idea Miner

Extract trading-skill ideas from Codex conversations and score them in the current
conversation. Use `references/idea_extraction_rubric.md` for the evidence rubric.

## Workflow

1. Use the current conversation or the user's selected chats/session exports.
   For a specified Codex chat use the available chat-reading tools; for supplied
   files read their actual format. If no source was identified, ask for the
   intended chats or project scope. Do not sweep unrelated private sessions.
2. Find repeated skill usage, repeated tool sequences, errors, explicit automation
   requests, and unresolved requests. Preserve evidence and source chat/file IDs.
   Use the requested period, or the previous seven days for a weekly refresh.
3. Read existing `skills/*/SKILL.md` metadata and the selected backlog. Reuse the
   pure deduplication helpers in `scripts/score_ideas.py` if useful; do not call
   its Claude-backed scoring entrypoint or the Claude-only session log parser.
4. Score novelty, feasibility, and trading value from 0–100 using actual evidence.
   Composite = 0.3 * novelty + 0.3 * feasibility + 0.4 * trading_value.
   Explain uncertain scores; do not invent session counts or requests.
5. Return `raw_candidates.yaml` and the scored backlog when requested, preserving
   the upstream schemas shown below. A dry run previews without modifying files.
   Before merging, read the existing backlog and preserve unrelated entries.

```yaml
generated_at_utc: "<actual UTC timestamp>"
period: {from: "<start date>", to: "<end date>"}
projects_scanned: []
sessions_scanned: 0
candidates:
  - id: "raw_<period>_001"
    title: "<evidence-based idea>"
    source_project: "<source>"
    evidence:
      user_requests: []
      pain_points: []
      frequency: 1
    raw_description: "<description>"
    category: "<category>"
```

```yaml
updated_at_utc: "<actual UTC timestamp>"
ideas:
  - id: "idea_<period>_001"
    title: "<title>"
    description: "<description>"
    category: "<category>"
    scores: {novelty: 75, feasibility: 60, trading_value: 80, composite: 73}
    status: pending
```

## Compatibility

The retained `mine_session_logs.py`, scoring CLI, and root
`run_skill_generation_pipeline.py` are upstream Claude automation, not Codex
session readers. This port uses Codex-native reading and reasoning instead.
No scheduler or background mining is installed.
