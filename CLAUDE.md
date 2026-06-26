# CLAUDE.md

Guidance for Claude Code working in this repository.

## Primary skill
For any Swift / iOS / iPadOS **game** task, use the **`swift-ios-game-studio`** skill —
invoke it as `/swift-ios-game-studio`. It is installed at
[`.claude/skills/swift-ios-game-studio/SKILL.md`](.claude/skills/swift-ios-game-studio/SKILL.md)
and mirrored from the canonical source at
[`.agents/skills/swift-ios-game-studio/`](.agents/skills/swift-ios-game-studio/).

The skill covers simple 2D games: coloring, jigsaw/sliding puzzles, light platformers,
drag-and-drop, memory/matching, lite endless runners, tap-reaction, and educational mini-games.
Read its SKILL.md and follow the execution workflow before writing code.

## Subagents (14 specialist roles)
Fourteen project subagents live in `.claude/agents/` (generated from canonical specs in
`.agents/agents/`). Invoke one with `@<name>` or just describe the need and let Claude route by
each agent's `description`.
- **Build:** `game-coordinator` (PM/decompose) → `game-designer` → `engine-architect` →
  `gameplay-programmer` (+ `art-director`, `narrative-writer`, `balance-economist` in parallel) → `qa-tester`.
- **Review & audit (read-only):** `code-reviewer` (diff/PR), and the pre-release gate —
  `code-auditor` (whole codebase), `security-auditor`, `performance-auditor`, `legal-compliance`.
- **Release:** `release-engineer` — App Store submission readiness (icons, Info.plist,
  archive/export, App Store Connect, privacy labels, TestFlight).

Subagents can't spawn each other, so `game-coordinator` returns a delegation plan for the main
thread to execute step by step. See `.agents/agents/README.md`.

## Source of truth & sync
- **Canonical skill:** `.agents/skills/swift-ios-game-studio/`. Edit it there.
- **Canonical agents:** `.agents/agents/`. Edit there, then regenerate tool copies.
- After editing, mirror into tool copies:
  ```bash
  .agents/skills/swift-ios-game-studio/scripts/sync-skill.sh   # skill -> .claude/.cursor
  .agents/agents/sync-agents.py                                # agents -> .claude/.cursor
  ```

## Project conventions
- **Logic vs rendering:** pure Swift model (no SwiftUI/SpriteKit imports) holds all rules and
  is unit-tested; SwiftUI views and `SKScene`s stay thin.
- **State machine:** menu → playing → paused → win/lose → menu.
- **Layout:** `App/ Models/ Systems/ Scenes/ Views/ Resources/ Tests/`. Small, focused files.
- **Mode choice:** SwiftUI-only for static/turn-based; SpriteKit for motion/physics;
  hybrid (`SpriteView`) for action games that also need real menus/HUD.
- **Assets:** no copyrighted material — placeholder vector shapes / SF Symbols, or user-owned
  assets only. Levels as JSON data, not code.
- **Dependencies:** Apple frameworks preferred; justify any third-party package.
- **Accessibility:** label/value/trait on every interactive control; Dynamic Type; Reduce Motion;
  VoiceOver.
- **Kids apps:** no tracking/analytics/ads/external-links/accounts; offline-first; no personal
  data; minimal permissions; parental gate for sensitive actions.

## Verification expectations
- Discover commands with `scripts/verify-ios-project.sh`; build/test with `xcodebuild` only when
  a scheme + destination are known. Swift packages: `swift build` / `swift test`.
- **Report honestly.** Only claim a build or tests passed if you ran them and saw the output. If
  you can't build here (no project / no toolchain), state that and give the exact commands.
- Run `assets/review-checklist.md` before handoff. **No compliance guarantees** — provide a
  checklist and a risk list instead.

## Handoff format
Finish with: what was built, mode chosen and why, **changed files**, **commands run + real
output** (or why none ran), assumptions, and open risks/next steps.
