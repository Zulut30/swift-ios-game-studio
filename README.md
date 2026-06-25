# swift-ios-game-studio

[![CI](https://github.com/Zulut30/swift-ios-game-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/Zulut30/swift-ios-game-studio/actions/workflows/ci.yml)

A portable **Agent Skill** that lets an AI coding agent (Codex, Claude Code, Cursor) build
simple, polished 2D games for iPhone and iPad in Swift — and write **excellent Swift** doing it.

Covered genres: coloring books, jigsaw/sliding puzzles, light platformers, drag-and-drop puzzles,
memory/matching card games, lite endless runners, tap-reaction, and educational mini-games.

## What's here
```
.
├─ .agents/skills/swift-ios-game-studio/   ← CANONICAL skill (edit here)
│  ├─ SKILL.md                             ← operational entry point + workflow
│  ├─ references/                          ← game pipeline, architecture, a11y, testing, perf…
│  │  └─ swift/                            ← Swift language mastery (write excellent Swift)
│  ├─ assets/                              ← templates: GDD, level schema, scenes, RNG, privacy
│  └─ scripts/                             ← sync, verify-ios-project, scaffold-game-module
├─ .agents/agents/                         ← CANONICAL subagents (8 specialist roles) + sync-agents.py
├─ .claude/skills/…  .claude/agents/       ← mirrors for Claude Code   (synced)
├─ .cursor/skills/…  .cursor/rules/agents/ ← mirrors for Cursor        (synced)
├─ .cursor/rules/                          ← Cursor .mdc rules (broad / architecture / testing)
├─ examples/MemoryMatch/                   ← complete, buildable & TESTED reference game
├─ docs/ai-game-dev/                       ← example prompts, eval prompts, troubleshooting
├─ AGENTS.md                               ← Codex entry point
└─ CLAUDE.md                               ← Claude Code entry point
```

## Specialist subagents
Twelve roles collaborate on larger games (canonical in `.agents/agents/`, mirrored to
`.claude/agents/` and `.cursor/rules/agents/`):
- **Build:** `game-coordinator` → `game-designer` → `engine-architect` → `gameplay-programmer`
  (+ `narrative-writer`, `balance-economist`) → `qa-tester`.
- **Review & audit (read-only):** `code-reviewer` (diff/PR) + the pre-release gate —
  `code-auditor` (whole codebase), `security-auditor`, `performance-auditor`, `legal-compliance`.

Regenerate tool copies with `.agents/agents/sync-agents.py`. See
[`.agents/agents/README.md`](.agents/agents/README.md).

## How the agent uses it
1. Reads `SKILL.md` and follows the workflow: understand → Mini-GDD → pick mode
   (SwiftUI / SpriteKit / hybrid) → architecture → MVP → tests → build/test → review → handoff.
2. Writes excellent Swift by meeting the 10-point quality bar in
   [`references/swift/README.md`](.agents/skills/swift-ios-game-studio/references/swift/README.md).
3. Mirrors the architecture of the worked example in
   [`examples/MemoryMatch/`](examples/MemoryMatch/).

## Invoke it
- **Claude Code:** `/swift-ios-game-studio` (or just describe a Swift/iOS game task; `CLAUDE.md` routes).
- **Cursor:** automatic via `.cursor/rules/swift-ios-game-studio.mdc` (always on); skill copy in `.cursor/skills/`.
- **Codex / AGENTS.md tools:** `AGENTS.md` at the repo root points to the skill.

## Develop the skill
- **Edit only** `.agents/skills/swift-ios-game-studio/`. Then mirror to the tool copies:
  ```bash
  .agents/skills/swift-ios-game-studio/scripts/sync-skill.sh          # copy canonical → .claude/.cursor
  .agents/skills/swift-ios-game-studio/scripts/sync-skill.sh --check  # CI: fail if copies drift
  ```
- **Verify the example builds & tests:**
  ```bash
  cd examples/MemoryMatch && swift build && swift test
  ```
- **Run the full quality gate** (also enforced in CI on every push/PR):
  ```bash
  .agents/skills/swift-ios-game-studio/scripts/validate-skill.sh   # frontmatter, sync, JSON, plist, globs
  ```
- **Scaffold a new game module:**
  ```bash
  .agents/skills/swift-ios-game-studio/scripts/scaffold-game-module.py --name SpaceJump --type simple-platformer
  ```

## Guarantees & limits
The skill enforces no copyrighted assets, a testable logic core, accessibility, and privacy-first
defaults for kids' apps. It does **not** guarantee App Store / COPPA / Kids Category approval —
it produces a checklist and a risk list. See
[`assets/review-checklist.md`](.agents/skills/swift-ios-game-studio/assets/review-checklist.md).
