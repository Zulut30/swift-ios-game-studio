# Troubleshooting

Common issues when building simple Swift iOS games and using this skill.

## Skill not triggering
- **Symptom:** the agent ignores `swift-ios-game-studio`.
- **Fix (Claude Code):** invoke explicitly with `/swift-ios-game-studio`. Ensure
  `.claude/skills/swift-ios-game-studio/SKILL.md` exists (run `scripts/sync-skill.sh`).
- **Fix (Cursor):** ensure `.cursor/rules/swift-ios-game-studio.mdc` exists and `alwaysApply: true`.
- **Fix (Codex):** ensure `AGENTS.md` is present at the repo root and points to the skill.
- **Check frontmatter:** SKILL.md `name:` must equal the folder name `swift-ios-game-studio`.

## Copies are stale
- **Symptom:** `.claude` / `.cursor` skill differs from canonical.
- **Fix:** edit only `.agents/skills/swift-ios-game-studio/`, then run
  `.agents/skills/swift-ios-game-studio/scripts/sync-skill.sh`. Use `DRY_RUN=1` to preview.

## xcodebuild can't find a scheme
- Run `xcodebuild -list -project <Name>.xcodeproj` (or `-workspace`) to see real scheme names.
- The scheme must be **shared** (Xcode ▸ Manage Schemes ▸ Shared) to be visible to CI/agents.
- Use `scripts/verify-ios-project.sh` to discover container + schemes first.

## "Unable to find a destination" / simulator errors
- List devices: `xcrun simctl list devicetypes` and `xcrun simctl list devices available`.
- Use an installed simulator name, e.g. `-destination 'platform=iOS Simulator,name=iPhone 15'`.
- If none are installed, open Xcode once to install a simulator runtime.

## Code signing blocks a simulator build
- For simulator builds you don't need signing: add `CODE_SIGNING_ALLOWED=NO` (the verify script
  already does). Real-device/archive builds need a team and provisioning.

## Model isn't unit-testable
- **Cause:** game rules leaked into SwiftUI/SpriteKit. **Fix:** move rules into pure Swift types
  with no UI imports; the view/scene should only render and forward intents.
- Mark the test target `@testable import GameName` and keep the model `internal` (not `private`)
  where tests need it; expose seams (e.g. seeded init, `matchAllForTesting()`).

## SpriteKit frame drops / hitches
- Pool and recycle nodes (don't create/destroy per spawn). Atlas textures so sprites batch.
- Turn on `view.showsFPS`, `showsNodeCount`, `showsDrawCount`; profile with Instruments.
- Advance by clamped `dt`; pause the scene on static/menu screens. See `performance-checklist.md`.

## Double-jump / tunneling bugs (platformer/runner)
- Gate jumps on real ground contact (`onGround`), not just a tap.
- Cap velocity and use reasonable body sizes to avoid fast objects passing through thin walls.

## Drag-and-drop pieces snap wrong / disappear under others
- Raise the active piece's z-order while dragging; restore on drop.
- Compute the nearest valid slot in the model; animate snap or bounce-back from there.

## Memory game accepts input during the mismatch flip-back
- Briefly **lock** the board between the second flip and the flip-back; ignore taps while locked.

## Layout breaks on iPad or in landscape
- Don't hardcode points. Drive layout from a design canvas + safe area; use `GeometryReader`/
  size classes (SwiftUI) or `scene.scaleMode` + camera (SpriteKit). Test both orientations.

## VoiceOver can't navigate the game
- Add `.accessibilityLabel/Value/AddTraits` to interactive elements; hide decorative nodes with
  `.accessibilityHidden(true)`; ensure a logical focus order. See `accessibility-child-safety.md`.

## Worried about App Store / Kids Category rejection
- This skill reduces common mistakes but **cannot guarantee** approval. Run
  `assets/review-checklist.md`, fix what you can, and review the current App Store Review
  Guidelines (and applicable law) yourself or with counsel. Present risks, not promises.

## scaffold script "did nothing"
- It is **non-destructive** and skips files that already exist (printed under "Skipped"). Delete
  or rename the existing files, or scaffold into a fresh `--dest`, if you want regenerated stubs.
