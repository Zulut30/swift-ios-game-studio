# Mini Game Design Document — <GAME NAME>

> One page. The contract for the MVP. Fill every section; keep it lean.

## 1. Concept
- **One-liner:** <what the game is in a sentence>
- **Genre / template:** <coloring-shapes | simple-platformer | drag-and-drop-puzzle | memory-cards | shape-matching | endless-runner-lite | tap-reaction>
- **Audience & age:** <e.g. ages 4–8>
- **Platforms:** iPhone / iPad / both · Orientation: portrait / landscape / both
- **Implementation mode:** SwiftUI-only / SpriteKit / Hybrid

## 2. Core loop
<The 1–3 step loop the player repeats. e.g. "Pick a color → tap a region → it fills → repeat.">

## 3. Controls / core verb
- **Primary verb:** <tap | drag | swipe | move>
- **Inputs:** <gestures/buttons and what they do>

## 4. Win / lose / progression
- **Failure model:** no-fail / score-chase / win-lose with retries
- **Win condition:** <…>
- **Lose condition (if any):** <…>
- **Progression:** <levels, difficulty ramp, unlocks — keep MVP small>

## 5. Art direction
- **Style:** bright, high-contrast placeholder vector shapes (no copyrighted assets)
- **Palette:** <6–8 friendly colors>
- **Key shapes / entities:** <player, tiles, targets…>

## 6. Audio
- **SFX:** <tap, win, etc. — optional, muteable>
- **Music:** <optional/none for MVP>
- **Defaults:** mute toggle present; conservative default

## 7. Accessibility
- Labels/values/traits on all controls · Dynamic Type · Reduce Motion · VoiceOver path
- Playable without reading text and without relying on color alone
- Touch targets ≥ 44pt (larger for young kids)

## 8. Child safety & privacy
- No tracking / analytics / ads / external links / accounts
- Collects no personal data; local progress/settings only; network off by default
- Sensitive actions (if any) behind a parental gate

## 9. Architecture sketch
- **Model:** <pure Swift types & rules>
- **State machine:** menu → playing → paused → win/lose → menu
- **Systems:** <input, score, spawn, collision, audio, save — as needed>
- **Folders:** App / Models / Systems / Scenes / Views / Resources / Tests

## 10. Scope
- **In (MVP):** <bullet the smallest set that delivers the core loop end-to-end>
- **Cut-line (later):** <everything deferred>

## 11. Success criteria
- <Measurable, e.g. "Player completes one level start→finish at 60fps with VoiceOver on.">

## 12. Assumptions & risks
- **Assumptions:** <documented defaults you applied>
- **Risks:** <open questions, compliance items — no guarantees>
