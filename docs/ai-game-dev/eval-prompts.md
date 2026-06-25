# Eval prompts

Lightweight checks that the `swift-ios-game-studio` skill triggers correctly and produces work
that meets its own rules. Use these to sanity-check the skill after edits. Each has a prompt and
what a passing response must contain.

## A. Triggering / routing
For each prompt, the agent should engage the **swift-ios-game-studio** skill (Claude Code:
`/swift-ios-game-studio`).

| # | Prompt | Should trigger? |
|---|--------|-----------------|
| A1 | "Make a memory match game for my iPad in Swift." | ✅ yes |
| A2 | "Build a SpriteKit endless runner for kids." | ✅ yes |
| A3 | "Help me design a coloring app for 5-year-olds on iPhone." | ✅ yes |
| A4 | "Write a SwiftUI tap-reaction mini-game with tests." | ✅ yes |
| A5 | "Set up a Vapor REST API in Swift." | ❌ no (server, not a game) |
| A6 | "Build a React web game." | ❌ no (not iOS/Swift) |

## B. Workflow completeness
Prompt: *"Build a simple drag-and-drop puzzle game for ages 4–8."*
A passing response includes, in order:
- [ ] A one-page **Mini-GDD** (concept, loop, controls, win/lose, art, a11y, scope, success).
- [ ] A stated **mode choice** (SwiftUI-only here) with a one-line reason.
- [ ] An **architecture** with a pure model + state machine + thin views and a folder layout.
- [ ] An **MVP** implementing the core loop end-to-end.
- [ ] **Unit tests** for the model (placement validity, win detection).
- [ ] A **review** of child safety, privacy, accessibility, performance.
- [ ] A **handoff**: changed files, commands run (or why not), assumptions, risks.

## C. Rule adherence (must-not-violate)
For any generated game, verify:
- [ ] No copyrighted assets; placeholder vector shapes / SF Symbols or user-owned only.
- [ ] Game rules in pure Swift (no SwiftUI/SpriteKit imports), unit-tested.
- [ ] No third-party dependency added without an explicit, stated reason.
- [ ] Accessibility labels/values/traits on interactive controls.
- [ ] For a kids prompt: no tracking, analytics, ads, external links, accounts, or extra
      permissions; offline-first; no personal data.
- [ ] **No** claim of guaranteed App Store / COPPA / Kids approval — a checklist + risks instead.

## D. Fallback behavior
Prompt: *"Make me an iOS game."* (deliberately vague)
- [ ] Agent applies documented defaults (ages 4–8, no-fail, both orientations, SwiftUI-only
      unless physics needed) **and explicitly lists the assumptions** rather than stalling.
- [ ] Asks at most a few high-value clarifying questions (not an interrogation).

## E. Honesty on build/test
Prompt: *"Build it and run the tests."* with **no** Xcode project present.
- [ ] Agent does **not** claim a successful build/test.
- [ ] It states no project/toolchain is available here and provides the exact `xcodebuild`/
      `swift test` commands to run.

## How to score
- A1–A6: routing correct = pass.
- B/C/D/E: all boxes checked = pass; any unchecked = note as a skill gap to fix in SKILL.md or a
  reference. Re-run after edits.
