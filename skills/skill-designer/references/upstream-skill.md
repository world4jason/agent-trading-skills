---
name: skill-designer
description: Design Codex trading skills from structured idea specifications. Use when a trading-skill backlog item or JSON idea needs a skill directory with instructions, references, scripts, and tests following this bundle's conventions.
---

## Codex execution

Before running this skill, read [Codex runtime](/Users/world4jason/.codex/skill-bundles/codex-trading-skills/CODEX_RUNTIME.md). It defines this installation's interpreter, resource paths, available-tool mapping, and external prerequisites.


# Skill Designer

## Overview

Generate a comprehensive Codex prompt from a structured skill idea
specification. The prompt instructs Codex to create a complete skill directory
following repository conventions: SKILL.md with YAML frontmatter, reference
documents, helper scripts, and test scaffolding.

## When to Use

- The skill auto-generation pipeline selects an idea from the backlog and needs
  a design prompt for the current Codex conversation
- A developer wants to bootstrap a new skill from a JSON idea specification
- Quality review of generated skills requires awareness of the scoring rubric

## Prerequisites

- Python 3.9+
- No external API keys required
- Reference files must exist under `references/`

## Workflow

### Step 1: Prepare Idea Specification

Accept a JSON file (`--idea-json`) containing:
- `title`: Human-readable idea name
- `description`: What the skill does
- `category`: Skill category (e.g., trading-analysis, developer-tooling)

Accept a normalized skill name (`--skill-name`) that will be used as the
directory name and YAML frontmatter `name:` field.

### Step 2: Build Design Prompt

Run the prompt builder:

```bash
python3 skills/skill-designer/scripts/build_design_prompt.py \
  --idea-json /tmp/idea.json \
  --skill-name "my-new-skill" \
  --project-root .
```

The script:
1. Loads the idea JSON
2. Reads all three reference files (structure guide, quality checklist, template)
3. Lists existing skills (up to 20) to prevent duplication
4. Outputs a complete prompt to stdout

### Step 3: Apply the prompt in Codex

Read the generated prompt and carry out the requested skill design in this
conversation using Codex file tools. Do not invoke a nested Claude CLI process.
Use the built-in [skill-creator](/Users/world4jason/.codex/skills/.system/skill-creator/SKILL.md) for Codex metadata and validation, while
preserving the user's chosen destination and the trading bundle's contracts.

### Step 4: Validate Output

After Codex creates the skill, verify:
- `skills/<skill-name>/SKILL.md` exists with correct frontmatter
- Directory structure follows conventions
- Score with dual-axis-skill-reviewer meets threshold

## Output Format

The script outputs a plain-text prompt to stdout. Exit code 0 on success,
1 if required reference files are missing.

## Resources

- `references/skill-structure-guide.md` -- Directory structure, SKILL.md format, naming conventions
- `references/quality-checklist.md` -- Dual-axis reviewer 5-category checklist (100 points)
- `references/skill-template.md` -- SKILL.md template with YAML frontmatter and standard sections
- `scripts/build_design_prompt.py` -- Prompt builder script (CLI interface)
