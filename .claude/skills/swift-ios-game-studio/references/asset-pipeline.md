# Asset pipeline

How to produce and organize art, audio, and level data without copyrighted material.

## Golden rule
**No copyrighted assets.** Do not add third-party characters, logos, brand fonts, sprite
rips, or licensed music/SFX. Use one of:
1. **Generated placeholder vector shapes** drawn in code (SwiftUI `Shape`/`Path`, SF Symbols,
   SpriteKit `SKShapeNode`).
2. **Assets the user explicitly provides and owns** (confirm ownership; place under `Resources/`).

## Placeholder art in code
Prefer drawing simple, bright, high-contrast shapes so the game is playable and pleasant
before any real art exists.

SwiftUI:
```swift
Circle().fill(.orange)                      // token / target
RoundedRectangle(cornerRadius: 12).fill(.blue)
Image(systemName: "star.fill")              // SF Symbols are fine to use
```
SpriteKit:
```swift
let node = SKShapeNode(circleOfRadius: 24)
node.fillColor = .systemGreen
node.strokeColor = .clear
```
- Build a tiny "art kit": a palette of 6–8 friendly colors and a set of primitive shapes.
- Keep everything vector so it scales crisply across iPhone/iPad and Retina densities.

## Asset catalog (when using image/user assets)
- Put images in `Assets.xcassets` with `@1x/@2x/@3x` or a single PDF/SVG marked
  "Preserve Vector Data" + "Single Scale".
- Use **App Icon** and **Accent Color** sets. Provide all required icon sizes for submission.
- Name assets semantically (`tile_grass`, `btn_jump`), not by appearance.
- Mark large textures for on-demand loading only if you actually need app thinning.

## Audio
- Use short, royalty-free or user-provided SFX only. Generate simple tones if nothing is provided.
- Formats: `.caf`/`.m4a` for SFX, keep files small. Provide a **mute toggle**; default conservative.
- SpriteKit: `SKAction.playSoundFileNamed`. SwiftUI: `AVAudioPlayer` wrapped in an `AudioSystem`.
- Never autoplay loud audio; respect the silent switch for non-essential sounds.

## Level / game data
Keep levels as **data, not code** so non-engineers can tweak and tests can load fixtures.
- Use JSON conforming to `assets/level-schema-template.json`.
- Decode with `Codable`; include a `schemaVersion`; fail gracefully on missing/extra keys.
- Store fixtures for tests under `Tests/Fixtures/`.

```swift
struct LevelData: Codable {
    var schemaVersion: Int
    var id: String
    var size: SizeData
    var entities: [EntityData]
}
```

## Naming & organization
```
Resources/
├─ Assets.xcassets/      // images, app icon, accent color (vector preferred)
├─ Levels/               // level_001.json, level_002.json ...
└─ Audio/                // sfx_tap.caf, sfx_win.caf (small, licensed/own/placeholder)
```

## Sizing & density
- Design against a logical canvas (e.g. 750×1334 portrait) and scale to the device.
- Provide art at sufficient resolution for iPad; vector avoids per-density exports.
- Test on the smallest and largest target devices; verify safe-area insets and notches.

## What NOT to do
- Don't fetch assets from the network at runtime for a kids' app.
- Don't embed analytics SDKs or tracking pixels in "asset" bundles.
- Don't ship huge unused textures; keep the bundle lean.
