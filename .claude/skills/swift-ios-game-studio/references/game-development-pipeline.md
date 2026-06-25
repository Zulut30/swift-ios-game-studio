# Game development pipeline

End-to-end process for taking a fuzzy game idea to a tested MVP. The SKILL.md workflow
summarizes this; here is the detail for each stage.

## 1. Discovery — understand the request
Capture, in one short paragraph each:
- **Core fantasy / goal** — what the player is doing and why it feels good.
- **Genre & reference** — coloring, puzzle, platformer, matching, runner, etc.
- **Audience & age** — drives difficulty, text load, safety, and motion.
- **Core verb** — tap, drag, swipe, tilt, move. One primary verb for a simple game.
- **Failure model** — no-fail (kids), score-chase, or win/lose with retries.
- **Session length** — seconds (tap-reaction) vs minutes (platformer level).
- **Platforms & orientation** — iPhone, iPad, both; portrait, landscape, both.

Ask only questions that change the architecture. Otherwise apply SKILL.md fallbacks and
record the assumptions.

## 2. Mini-GDD
Produce a one-page Game Design Document from `assets/gdd-template.md`. It is the contract
for the MVP. Keep it lean: concept, core loop, controls, progression/levels, art & audio
direction, accessibility notes, scope cut-line, and measurable success criteria.

## 3. Mode selection
Decide rendering mode using the decision rule in `ios-game-architecture.md`:
- No per-frame motion / physics → **SwiftUI-only**.
- Continuous motion, sprites, collisions, particles → **SpriteKit**.
- Action gameplay that also needs rich menus/HUD/settings → **Hybrid** (`SpriteView` in SwiftUI).

## 4. Architecture
- Define the **state machine**: `menu → playing → paused → (win | lose) → menu`.
- Split **model** (pure Swift rules/state) from **view** (SwiftUI/SpriteKit rendering).
- List the systems you need: input, scoring, spawn, collision, progression, audio, save.
- Sketch the folder layout (`Models/`, `Systems/`, `Scenes/`, `Views/`, `Resources/`).

## 5. MVP implementation
- Build the smallest version that delivers the core loop once, end to end.
- Start from the templates in `assets/` and the recipe in `game-templates.md`.
- Keep files small and single-purpose. No premature systems (no shop, no online).
- Use placeholder vector art (see `asset-pipeline.md`). No copyrighted assets.

## 6. Tests
- Unit-test the pure model: legal moves, scoring, win/lose, level load, state transitions.
- Add a couple of golden cases per level/format. See `testing-and-release.md`.

## 7. Build & verify
- If a project/workspace exists, run `scripts/verify-ios-project.sh`.
- Provide explicit `xcodebuild` commands. Report real output. If you cannot build, say so.

## 8. Review
- Run `assets/review-checklist.md`: child safety, privacy, accessibility, performance.

## 9. Handoff
Deliver a concise report:
- **Built:** the loop and features that work now.
- **Mode & why.**
- **Changed files:** list with one-line purpose each.
- **Commands run + output** (or why none could run).
- **Assumptions, risks, and next steps.** No compliance guarantees.

## Scope discipline
Define a cut-line in the GDD. Anything past the cut-line is "later". A polished tiny game
beats a broken big one — especially for kids' apps where reliability is the whole product.
