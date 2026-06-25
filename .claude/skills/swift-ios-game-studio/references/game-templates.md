# Game templates

Per-template recipes. Each gives: mode, core loop, model, view/scene, data, tests, and pitfalls.
Pick the closest and adapt. All use placeholder vector art — no copyrighted assets.

---

## coloring-shapes  (SwiftUI-only)
**Loop:** pick a color → tap a region → region fills. No fail state.
**Model:** `Region { id, path, fillColor: Color? }`, `Palette [Color]`, `Picture { regions }`.
`apply(color, toRegionAt:) ` sets the fill. Win = all regions filled (optional).
**View:** render regions as tappable `Shape`/`Path`; a palette bar; undo/clear buttons.
**Data:** regions as normalized path points in JSON (see `level-schema-template.json`).
**Tests:** filling a region updates only that region; undo restores previous color.
**Pitfalls:** hit-testing overlapping paths (use `.contentShape`); keep paths vector for crisp scaling.

## simple-platformer  (SpriteKit, hybrid shell)
**Loop:** move left/right, jump over gaps, reach the goal; fall = retry the level.
**Model:** `Player { position, velocity, onGround }`, `Level { platforms, hazards, goal }`,
tuning `{ gravity, jumpImpulse, moveSpeed }`. Pure stepping function advances physics-lite or
mirrors SpriteKit physics results into win/lose.
**Scene:** `SKSpriteNode` player, static platform bodies, contact delegate for goal/hazard.
**Input:** on-screen left/right + jump buttons (SwiftUI overlay) → intents.
**Data:** level layout JSON (platform rects, hazard rects, spawn, goal).
**Tests:** reaching goal → win; touching hazard or y<floor → lose; jump only when `onGround`.
**Pitfalls:** double-jump bugs (gate on ground contact), tunneling at high speed (cap velocity).

## drag-and-drop-puzzle  (SwiftUI-only)
**Loop:** drag a piece to its matching slot; correct → snaps & locks; wrong → bounces back.
**Model:** `Piece { id, correctSlot }`, `Slot { id, occupiedBy: PieceID? }`. `place(piece, in slot)`
returns valid/invalid. Win = all slots correctly occupied.
**View:** draggable pieces (`DragGesture`), slot targets, snap animation, completion celebration.
**Tests:** correct placement locks & counts toward win; wrong placement is rejected; win detection.
**Pitfalls:** z-order while dragging (raise active piece); snapping math; partial-overlap matching.

## memory-cards  (SwiftUI-only)
**Loop:** flip two cards; match keeps them face-up; mismatch flips back. No fail; track moves/time.
**Model:** `Card { id, symbol, isFaceUp, isMatched }`, `Board { cards }`. `flip(cardAt:)` with the
classic two-up rule. Win = all matched. Deterministic shuffle via injected seed for tests.
**View:** grid of cards with flip animation; moves & timer HUD; restart.
**Tests:** two matching symbols stay up; two different flip back after the second; win when all matched;
seeded shuffle is reproducible.
**Pitfalls:** input during the mismatch delay (lock board briefly); odd card counts; accessibility labels per card.

## shape-matching  (SwiftUI-only)
**Loop:** match a shown shape/color/number to the correct target slot. Reinforce on correct.
**Model:** `Item { kind }`, `Target { kind }`, `match(item, target) -> Bool`. Round-based; score++ on correct.
**View:** prompt item + 2–4 target options; positive feedback; next round.
**Tests:** correct match scores and advances; wrong match does not advance; round generation is valid.
**Pitfalls:** make distractors fair for the age; avoid relying on color alone (pair color with shape).

## endless-runner-lite  (SpriteKit, hybrid shell)
**Loop:** auto-run; tap to jump obstacles; speed ramps; one hit ends the run; score = distance/coins.
**Model:** `Runner { y, vy, alive }`, `Spawner` (deterministic with seed), `Score`. Step by dt.
**Scene:** parallax background, ground, recycled obstacle nodes (object pool), jump on tap.
**Tests:** collision ends run; jump arc; score increments with distance; seeded spawn reproducible.
**Pitfalls:** node churn (pool & recycle), difficulty ramp fairness, frame-independent speed (use dt).

## tap-reaction  (SwiftUI or SpriteKit)
**Loop:** targets appear; tap before they vanish; hit = score, miss/expire = penalty or just lower score.
**Model:** `Target { id, spawnTime, lifetime, position }`, `reactionTime`, `Score`. Time-driven.
**View:** spawn targets at random valid positions; shrink/fade timer; combo feedback.
**Tests:** tap within lifetime scores; expired target counts as miss; spawn positions stay on-screen.
**Pitfalls:** spawn overlap, fairness of lifetimes by age, RNG seeding for tests.

---

## Shared conventions
- **Deterministic RNG:** inject a seeded generator so shuffles/spawns are reproducible in tests.
- **No-fail option:** for young audiences, prefer soft feedback over hard game-over.
- **Celebrate success:** simple particle/scale animation on win; keep it short and skippable.
- **Accessibility:** every interactive element has a label/value/trait; don't gate play on reading.
- **Persistence:** save only progress/settings; nothing personal; no network.
