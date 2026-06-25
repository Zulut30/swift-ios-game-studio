---
name: swift-ios-game-studio
description: Build simple 2D iOS/iPadOS games in Swift — coloring books, jigsaw/sliding puzzles, light platformers, drag-and-drop puzzles, memory/matching card games, lite endless runners, tap-reaction, and educational mini-games. Use when a request involves Swift, SwiftUI, SpriteKit, GameplayKit, GameKit, an iPhone or iPad game, a kids/children's game, game architecture, level design, an asset pipeline, child-safety/privacy review, game testing, or Xcode/xcodebuild build & test. Produces a Mini-GDD, an MVP, tests, and a review checklist.
---

# Swift iOS Game Studio

Operational guide for building simple, polished 2D games for iPhone and iPad in Swift.
You are the implementer: produce a working MVP, keep core logic testable, and finish with
a child-safety / privacy / accessibility / performance review and an honest handoff.

## When to use
Trigger on any 2D iOS/iPadOS game task: coloring, puzzles, platformers, drag-and-drop,
memory/matching, lite arcades, tap-reaction, or educational mini-games. Trigger on
mentions of Swift, SwiftUI, SpriteKit, GameplayKit, GameKit, Xcode, or "kids app".

## Supported stack
Swift · SwiftUI · SpriteKit · GameplayKit (optional) · GameKit (optional) ·
Swift Testing & XCTest · Xcode / `xcodebuild`. Target: Universal iOS/iPadOS app,
portrait + landscape, iPhone + iPad adaptive, privacy-first defaults.

## Execution workflow
Run these steps in order. Skip a step only with a stated reason.

1. **Understand the game request.** Identify genre, target age, core verb (tap / drag /
   match / move), win/lose or "no-fail" model, session length, and platform constraints.
   Ask at most a few high-value questions; otherwise apply documented defaults (see Fallback).
2. **Generate a Mini-GDD.** Use `assets/gdd-template.md`. Keep it to one page: concept,
   core loop, controls, progression, art direction, audio, accessibility, success criteria.
3. **Select implementation mode:**
   - **SwiftUI-only** — static/turn-based boards, coloring, memory, matching, drag-and-drop,
     tap-reaction. No per-frame physics. Simplest and most testable.
   - **SpriteKit** — continuous motion, physics, sprites, particles: platformer, runner.
   - **Hybrid SwiftUI + SpriteKit** — SpriteKit gameplay inside a SwiftUI shell
     (menus, HUD, settings) via `SpriteView`. Default for action games that need real UI.
   See `references/swiftui-spritekit-patterns.md` and `references/ios-game-architecture.md`.
4. **Define architecture.** Separate pure game logic (model + rules + state machine) from
   rendering. Keep the model in plain Swift with no SpriteKit/SwiftUI imports so it is unit
   testable. Use a small state machine (menu → playing → paused → win/lose).
5. **Implement the MVP.** Start from `assets/swiftui-gameview-template.swift` and/or
   `assets/spritekit-scene-template.swift`. Small files, modular folders
   (`Models/`, `Systems/`, `Scenes/`, `Views/`, `Resources/`). Use the matching recipe in
   `references/game-templates.md`. **Write excellent Swift** — meet the Swift quality bar in
   `references/swift/README.md` and consult the matching `references/swift/*` file (language,
   API design, concurrency, SwiftUI, generics, memory, idioms). A fully worked, buildable
   reference game lives in `examples/MemoryMatch/` — mirror its structure.
6. **Add tests.** Cover the pure model: scoring, win/lose, valid moves, level loading,
   state transitions. Prefer Swift Testing (`import Testing`, `@Test`), XCTest is fine.
   See `references/testing-and-release.md`.
7. **Run build/test when available.** If an Xcode project/workspace exists, use
   `scripts/verify-ios-project.sh` to discover schemes and run a safe `xcodebuild` build/test.
   If you cannot build (no project, no toolchain), say so explicitly — do not claim it passed.
8. **Review.** Walk `assets/review-checklist.md`: child safety, privacy, accessibility,
   and performance. See `references/accessibility-child-safety.md` and
   `references/performance-checklist.md`.
9. **Handoff.** Report: what you built, the chosen mode and why, **changed files**,
   **commands run with their real output**, assumptions, open risks, and next steps.

## Game templates
Pick the closest and adapt (full recipes in `references/game-templates.md`):
- `coloring-shapes` — tap-to-fill vector regions with a palette. SwiftUI-only.
- `simple-platformer` — run/jump on platforms, simple physics. SpriteKit (hybrid shell).
- `drag-and-drop-puzzle` — drag pieces to slots / snap-to-grid. SwiftUI-only.
- `memory-cards` — flip-and-match pairs, no-fail. SwiftUI-only.
- `shape-matching` — match shape/color to target slot. SwiftUI-only.
- `endless-runner-lite` — auto-run, tap to jump, increasing speed. SpriteKit (hybrid).
- `tap-reaction` — tap targets before they vanish; reaction scoring. SwiftUI or SpriteKit.

## Strict rules
- **No copyrighted assets.** Generate placeholder vector shapes / simple system-drawn art,
  or use only assets the user explicitly provides and owns. No third-party characters,
  logos, fonts, music, or sprites.
- **Minimal dependencies.** Prefer Apple frameworks only. Add a third-party package solely
  with a strong, stated reason and the user's awareness.
- **Testable core.** Game logic must run and be tested outside SpriteKit/SwiftUI.
- **Small, modular files.** Many focused files over a few large ones.
- **Accessibility.** Every interactive control gets an accessibility label/value/trait;
  respect Dynamic Type, Reduce Motion, and VoiceOver. See child-safety reference.
- **Children's apps:** no external links, no tracking, no third-party analytics, no ads,
  no IDFA/ATT, no dark patterns, and request no unnecessary permissions. Privacy-first.
- **No compliance guarantees.** Never claim guaranteed App Store / COPPA / Kids Category
  approval. Produce a checklist and an honest risk list instead.

## Fallback behavior (defaults when details are missing)
If the user is vague, build a small polished MVP and document every assumption:
- Audience: ages 4–8, **no-fail / low-stress** design.
- Orientation: support both; design portrait-first on iPhone, adapt for iPad.
- Mode: SwiftUI-only unless the genre needs physics/continuous motion.
- Art: bright, high-contrast placeholder vector shapes; no text-reading required to play.
- Audio: gentle optional SFX with a mute toggle; off by default if unsure.
- Persistence: lightweight (`UserDefaults` / a small Codable file) for progress only.
- No networking, no accounts, no analytics. State these choices in the Mini-GDD and handoff.

## Reference map
- `references/game-development-pipeline.md` — end-to-end process & the Mini-GDD step.
- `references/ios-game-architecture.md` — layers, state machine, testable-core pattern.
- `references/swiftui-spritekit-patterns.md` — SwiftUI/SpriteKit interop, game loop, input.
- `references/game-templates.md` — per-template recipes, structures, and pitfalls.
- `references/asset-pipeline.md` — placeholder art, asset catalogs, audio, level data.
- `references/accessibility-child-safety.md` — a11y APIs + kids-app safety/privacy rules.
- `references/testing-and-release.md` — unit tests, build/test commands, release checklist.
- `references/performance-checklist.md` — frame budget, node/draw counts, memory, battery.
- `references/gameplaykit-gamekit.md` — optional: GKStateMachine, deterministic GKRandomSource,
  ECS, agents/pathfinding; GameKit (Game Center) with kids-safety caveats.
- `references/haptics-and-guided-access.md` — tactile feedback (UIFeedbackGenerator / Core
  Haptics) and Guided Access (device lock-in for kids).

### Swift mastery (write excellent Swift) — `references/swift/`
- `references/swift/README.md` — index + the 10-point Swift quality bar (start here).
- `references/swift/swift-language-essentials.md` — value/reference types, optionals, enums, errors.
- `references/swift/swift-api-design.md` — naming & API design; illegal states unrepresentable.
- `references/swift/swift-protocols-generics.md` — protocols, generics, `some`/`any`, seams.
- `references/swift/swift-concurrency.md` — async/await, actors, `@MainActor`, Swift 6 Sendable.
- `references/swift/swiftui-mastery.md` — SwiftUI state, layout, animation, gestures, a11y, perf.
- `references/swift/swift-memory-performance.md` — ARC, retain cycles, COW, pooling, profiling.
- `references/swift/swift-patterns-idioms.md` — result builders, property wrappers, KeyPaths, RNG.

## Worked example
- `examples/MemoryMatch/` — a complete, buildable & tested reference game: a pure Swift Package
  core (`swift test` green) plus SwiftUI UI files. Copy its architecture for new games.

## Assets (copy & adapt)
- `assets/gdd-template.md`, `assets/level-schema-template.json`,
  `assets/spritekit-scene-template.swift`, `assets/swiftui-gameview-template.swift`,
  `assets/review-checklist.md`.
- `assets/seeded-random.swift` — drop-in seedable `RandomNumberGenerator` for deterministic,
  testable shuffles/spawns.
- `assets/PrivacyInfo.xcprivacy` — "Data Not Collected" privacy manifest template for kids/
  privacy-first apps (adjust honestly to what the app actually does).
- `assets/example-level.json` — a valid sample level conforming to `level-schema-template.json`;
  use as a starting point and a validation fixture.
- `assets/swift-format.json` — recommended `swift-format` config (4-space, line length 110) that
  matches the Swift quality bar; drop it into a project as `.swift-format` and enforce with
  `swift format lint --strict`.

## Scripts
- `scripts/sync-skill.sh` — mirror this canonical skill into `.claude/` and `.cursor/`
  (`--check` fails on drift for CI).
- `scripts/verify-ios-project.sh` — find project/workspace, list schemes, safe build/test.
- `scripts/scaffold-game-module.py` — create a non-destructive module skeleton for a genre.
- `scripts/validate-skill.sh` — structural quality gate (frontmatter, name==folder, sync,
  JSON/plist validity, script syntax, Cursor `globs` format). Run before committing skill changes.
- `scripts/validate-levels.py` — validate level JSON files against `level-schema-template.json`
  (uses `jsonschema` if installed, else a dependency-free built-in validator).
