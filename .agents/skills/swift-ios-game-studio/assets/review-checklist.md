# Review checklist — <GAME NAME>

Run before handoff. Check each box or note why it doesn't apply. This is a quality gate,
**not** a guarantee of App Store / COPPA / Kids Category approval — produce risks, not promises.

## Child safety & privacy (kids-app defaults)
- [ ] No third-party analytics, tracking, fingerprinting, or IDFA/ATT prompt.
- [ ] No ads (especially no targeted/behavioral ads).
- [ ] No external links / web views out of the app in the child-facing flow.
- [ ] No accounts, login, or sign-in wall for core play.
- [ ] Collects no personal data; stores only local progress/settings.
- [ ] Requests only strictly necessary permissions (each with a clear usage string).
- [ ] Network off by default; offline-first.
- [ ] No dark patterns; any IAP/links to purchases sit behind a parental gate.
- [ ] `PrivacyInfo.xcprivacy` accurate ("Data Not Collected" if true).

## Accessibility
- [ ] Every interactive control has an accessibility label (+ value/trait where useful).
- [ ] Playable without reading text and without relying on color alone.
- [ ] Honors Dynamic Type; layouts survive the largest accessibility text sizes.
- [ ] Honors Reduce Motion (replaces large motion with fades).
- [ ] VoiceOver: logical focus order; decorative nodes hidden; key state changes announced.
- [ ] Touch targets ≥ 44pt (larger for young children); generous spacing.
- [ ] A relaxed / no-timer option exists if timing is a core challenge.

## Architecture & code quality
- [ ] Game rules live in pure Swift (no SwiftUI/SpriteKit imports) and are unit-tested.
- [ ] Clear state machine: menu → playing → paused → win/lose → menu.
- [ ] Small, single-purpose files; sensible folders (Models/Systems/Scenes/Views/Resources/Tests).
- [ ] No copyrighted assets; placeholder vector art or user-owned assets only.
- [ ] Minimal dependencies (Apple frameworks preferred); any 3rd-party dep justified.
- [ ] Deterministic RNG (seeded) where shuffles/spawns are tested.

## Performance
- [ ] Updates use clamped `dt` (frame-rate independent).
- [ ] Steady target fps on the oldest supported device; no hitches in normal play.
- [ ] Node/draw counts bounded; off-screen nodes removed; pools used for spawners.
- [ ] Textures atlased & right-sized; no oversized images; memory stable over a long session.
- [ ] No render loop on static/paused screens; audio stops when idle.

## Functionality / QA
- [ ] Core loop completes start→finish; win and (if any) lose paths work.
- [ ] iPhone and iPad layouts both correct; portrait & landscape as designed; safe areas respected.
- [ ] Background/foreground mid-game preserves state; no `dt` spike; audio pauses/resumes.
- [ ] Restart/replay works; persistence survives relaunch.
- [ ] No debug logging, placeholder copy, or TODOs shipped in the play path.

## Build & tests
- [ ] Builds (debug) for simulator; if a real project exists, command + output recorded.
- [ ] Unit tests for model pass; command + output recorded.
- [ ] If not built/tested here, that is stated explicitly with the commands to run.

## Handoff completeness
- [ ] Changed files listed with one-line purpose each.
- [ ] Commands run + real output (or explicit "not run here").
- [ ] Assumptions documented; open risks listed; next steps proposed.
- [ ] No compliance guarantees made.
