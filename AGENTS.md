# AGENTS.md

Guidance for coding agents (Codex and any AGENTS.md-aware tool) working in this repo.

## Primary skill
For any Swift / iOS / iPadOS **game** task, use the **`swift-ios-game-studio`** skill.
Canonical location: [`.agents/skills/swift-ios-game-studio/SKILL.md`](.agents/skills/swift-ios-game-studio/SKILL.md).
It covers simple 2D games: coloring, puzzles, platformers, drag-and-drop, memory/matching,
lite runners, tap-reaction, and educational mini-games.

Read the SKILL.md first, then follow its execution workflow:
understand → Mini-GDD → pick mode (SwiftUI / SpriteKit / hybrid) → architecture → MVP →
tests → build/test → review (child safety, privacy, a11y, performance) → handoff.

Deep-dive references live in `.agents/skills/swift-ios-game-studio/references/`,
copy-and-adapt templates in `assets/`, and helper scripts in `scripts/`.

## Subagents (specialist roles)
For larger game work, play the specialist roles defined in `.agents/agents/` (canonical specs).
When asked to "act as the <role> agent", read that file and adopt its responsibilities and output
format. The pipeline:

1. `game-coordinator` — decompose the task, sequence subtasks, decide who's next (first).
2. `game-designer` — mechanics, core loop, progression, economy concept, Mini-GDD.
3. `engine-architect` — mode (SwiftUI/SpriteKit/hybrid), architecture, perf budget, seams.
4. `gameplay-programmer` — implement systems, abilities, interaction logic, UI flow.
5. `narrative-writer` — quests, copy, lore, tutorial flow, localized strings (parallel).
6. `balance-economist` — difficulty/progression curves, economy, win-rate/tempo (parallel).
7. `qa-tester` — test cases, unit tests, edge cases, accessibility, runs build/tests.
8. `code-reviewer` — bugs, style, architecture violations vs the skill + Swift quality bar (last).

Every role enforces the same contract: no copyrighted assets, testable UI-free logic core,
accessibility, kids safety/privacy, the Swift quality bar, and no compliance guarantees.
See `.agents/agents/README.md`.

## Build & test command discovery
Do not assume commands — discover them:
1. Run `.agents/skills/swift-ios-game-studio/scripts/verify-ios-project.sh` to detect a
   project/workspace and list schemes.
2. Build/test only when a scheme + destination are known:
   ```bash
   xcodebuild -list -project <Name>.xcodeproj            # or -workspace <Name>.xcworkspace
   xcodebuild build -scheme <Scheme> -destination 'platform=iOS Simulator,name=iPhone 15'
   xcodebuild test  -scheme <Scheme> -destination 'platform=iOS Simulator,name=iPhone 15'
   ```
3. Swift Package targets: `swift build` / `swift test`.
4. **Honesty rule:** only report a build/test as passing if you actually ran it and saw it.
   If you can't build here, say so and provide the exact commands.

## Coding standards
- **Separate logic from rendering.** Game rules live in pure Swift (no SwiftUI/SpriteKit
  imports) so they are unit-testable. Views/scenes are thin.
- **State machine:** menu → playing → paused → win/lose → menu.
- **Small, modular files;** folders `App/ Models/ Systems/ Scenes/ Views/ Resources/ Tests/`.
- **Tests** for the model: legal moves, scoring, win/lose, level loading, transitions.
  Prefer Swift Testing; XCTest is fine. Seed RNG for deterministic shuffles/spawns.
- **No copyrighted assets.** Placeholder vector shapes / SF Symbols, or user-owned assets only.
- **Minimal dependencies** — Apple frameworks preferred; justify any third-party package.
- **Accessibility** on every interactive control (label/value/trait); honor Dynamic Type and
  Reduce Motion.
- **Children's apps:** no tracking, analytics, ads, external links, accounts, or unnecessary
  permissions; offline-first; collect no personal data; sensitive actions behind a parental gate.
- **No compliance guarantees.** Produce checklists and risks, never "App Store approved".

## Handoff format
End every task with: what was built, chosen mode and why, **changed files**, **commands run +
real output** (or why none ran), assumptions, and open risks/next steps.
