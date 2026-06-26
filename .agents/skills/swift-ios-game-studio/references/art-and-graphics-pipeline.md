# Art & graphics pipeline

How to produce **original** game art for this skill — as Swift drawing code, vectors, composed
SF Symbols, seeded generative art, sprite atlases, and light 3D — with a contrast-checked palette
and **zero copyrighted material**. This is the home of the `art-director` subagent's craft, and the
art analog of the logic core: deterministic, testable, theme-driven, UI-thin. Pairs with
[`asset-pipeline.md`](asset-pipeline.md) (organization, audio, level data) and
[`accessibility-child-safety.md`](accessibility-child-safety.md) (the color/kids rules).

## Golden rules (non-negotiable)
- **No copyrighted assets.** Generated-from-primitives/math, original tool-generated, or
  **confirmed user-owned** only. No tracing, fan art, brand/character meshes, or sprite/font/music
  rips. SF Symbols used as Apple's licensed font, not rasterized-and-redistributed.
- **Cheapest medium that meets the need.** `Shape`/`Canvas` first → SVG/PDF for hand-tuned flat art
  → raster/3D only when the design truly needs it.
- **Vector-first, resolution-independent.** Scales crisply on every iPhone/iPad density; ships as
  code (not binary blobs); animatable and themeable.
- **Accessible color, always redundant.** WCAG AA met and **reported** with real ratios; meaning
  carried by shape + symbol + label, never hue alone; decorative art hidden from VoiceOver; Reduce
  Motion honored.
- **Data, not magic numbers.** Palette tokens, frame metadata, pivots, fps, cap insets, variants
  live as data/JSON so the logic core stays render-free and testable.

## An LLM's honest limits (state these on handoff)
Authors reliably: **art-as-code** that compiles, **procedural/vector** assets, **precise specs**, and
palette math (deterministic, real numbers). Does **not** hand-paint raster/photographic art, sculpt
organic 3D, or bake a binary (`.png` sheet, `.usdz`) from nothing. For those: compose from
vectors/`Canvas`/noise/primitives, **or** write an exact original brief and **drive an image/3D-gen
MCP tool when one is connected** (Figma / Adobe Express / Reality Composer / text-to-3D), then
**re-gate** the output. Cannot self-preview — recommend an on-device/snapshot check. **No
pixel-perfect or licensed-look parity claim.**

---

## 1. Vector & procedural 2D (default path)

**SwiftUI `Shape` — reusable, animatable, themeable; the shape carries the meaning.**
```swift
struct StarToken: Shape {
    var points = 5
    func path(in rect: CGRect) -> Path {
        let c = CGPoint(x: rect.midX, y: rect.midY)
        let (rO, rI) = (rect.width / 2, rect.width / 4)
        var p = Path()
        for i in 0..<(points * 2) {
            let r = i.isMultiple(of: 2) ? rO : rI
            let a = .pi / Double(points) * Double(i) - .pi / 2
            let pt = CGPoint(x: c.x + cos(a) * r, y: c.y + sin(a) * r)
            i == 0 ? p.move(to: pt) : p.addLine(to: pt)
        }
        p.closeSubpath(); return p
    }
}
// StarToken().fill(Palette.coin) — color-blind-safe because the *shape* is the signal.
```

**Original SVG → PDF for the asset catalog** (one vector covers @1x/@2x/@3x — no per-density export):
```svg
<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Star token">
  <circle cx="50" cy="50" r="48" fill="#FFD54A"/>
  <path d="M50 18 L61 42 L87 44 L67 62 L73 88 L50 74 L27 88 L33 62 L13 44 L39 42 Z" fill="#FF8A3D"/>
</svg>
```
Ship as a **PDF** in `Assets.xcassets` marked *Preserve Vector Data* + *Single Scale*.

**SF Symbols — composed/recolored, not rasterized.** Label, never color, conveys identity:
```swift
Image(systemName: "leaf.fill")
    .symbolRenderingMode(.palette)
    .foregroundStyle(Palette.accent, Palette.coin)
    .accessibilityLabel("Plant")
```

**Core Graphics / `UIGraphicsImageRenderer`** only when a one-time bitmap is genuinely needed (a
baked texture or a share image) — otherwise stay vector.

---

## 2. Seeded generative art (reproducible = testable)

Inject `SeededGenerator` (`assets/seeded-random.swift`) — **same seed → same artwork**:
```swift
struct FlowFieldBackground: View {
    var seed: UInt64 = 42
    var body: some View {
        Canvas { ctx, size in
            var rng = SeededGenerator(seed: seed)          // same seed → same art (testable)
            for _ in 0..<400 {
                let x = Double.random(in: 0...size.width, using: &rng)
                let y = Double.random(in: 0...size.height, using: &rng)
                let angle = (sin(x * 0.01) + cos(y * 0.01)) * .pi   // deterministic field
                var dot = Path(); dot.move(to: .init(x: x, y: y))
                dot.addLine(to: .init(x: x + cos(angle) * 14, y: y + sin(angle) * 14))
                ctx.stroke(dot, with: .color(Palette.accent.opacity(0.5)), lineWidth: 2)
            }
        }
        .accessibilityHidden(true)   // decorative: hide from VoiceOver
        // Under Reduce Motion: render one static frame instead of animating the seed.
    }
}
```
Snapshot- or geometry-test the output for a fixed seed. Flow fields, particle scatters, value/
Perlin-style noise, lattices, confetti all follow this pattern.

---

## 3. Sprites, texture atlases & animation

Three deliverables for any sprite need: **(a)** a tool-agnostic atlas spec, **(b)** placeholder
art-as-code that plays immediately, **(c)** runtime animation/particle/9-slice code. An LLM cannot
*paint* frames — it produces (a)+(b)+(c), or drives a gen/vectorizer tool and verifies against (a).

**(a) Atlas spec — the contract.** Pivots normalized (0–1, origin bottom-left = SpriteKit anchor):
```jsonc
// art/specs/coin.atlas.json
{
  "atlas": "coin",                 // -> Coin.atlasc / Coin.spriteatlas
  "canvasFrame": [64, 64],         // @1x logical px; export @2x/@3x too
  "pivot": [0.5, 0.5], "padding": 2, "trim": true, "premultipliedAlpha": true,
  "palette": ["#F2B705", "#A66E00", "#FFFFFF"],     // kid-safe; AA-contrast vs bg
  "frames": [                      // ordered; name == file == texture key
    {"name": "coin_spin_000", "size": [64, 64]},
    {"name": "coin_spin_001", "size": [64, 64]},
    {"name": "coin_spin_002", "size": [64, 64]},
    {"name": "coin_spin_003", "size": [64, 64]}
  ],
  "animation": {"key": "spin", "fps": 12, "loop": true}
}
```
**Naming & layout** (deterministic, 1:1 with `SKTextureAtlas` / asset catalog): `actor_action_NNN`
(zero-padded → sorts in play order), semantic names (`tile_grass`, not `green32`), one atlas per
actor/screen to bound page count, constant pixel size across a cycle.
```
Resources/
├─ Coin.atlas/              coin_spin_000@2x.png  coin_spin_000@3x.png  ...
└─ UI.spriteatlas/          btn_primary.imageset/  (9-slice)
```

**(b) Placeholder art-as-code** — ships and plays before any real art exists:
```swift
func placeholderCoinTextures(view: SKView) -> [SKTexture] {
    (0..<4).map { i in
        let s = SKShapeNode(circleOfRadius: 24)
        s.fillColor = .systemYellow; s.strokeColor = .brown   // shape+stroke read w/o color
        s.xScale = 1 - CGFloat(i) * 0.4                        // fake the spin by squashing width
        return view.texture(from: s) ?? SKTexture()
    }
}
```

**(c) Frame animation** (`SKTextureAtlas` → `SKAction.animate`):
```swift
let atlas = SKTextureAtlas(named: "Coin")
let frames = atlas.textureNames.sorted().map { atlas.textureNamed($0) }  // name sort = play order
frames.forEach { $0.filteringMode = .nearest }                           // .linear for smooth art
let spin = SKAction.animate(with: frames, timePerFrame: 1.0/12.0, resize: false, restore: true)
coin.run(.repeatForever(spin), withKey: "spin")
// SKTextureAtlas.preload(_:) before a level to avoid first-play hitches.
// What the animation *means* (collected, hurt) lives in the model; the scene only plays frames.
```

**Particles** — kid-safe, **finite**, Reduce-Motion-aware (see `performance-checklist.md`):
```swift
func winConfetti() -> SKEmitterNode {
    let e = SKEmitterNode()
    e.particleColor = .systemTeal; e.particleColorSequence = nil
    e.numParticlesToEmit = 60          // FINITE — never an endless emitter on a kids' screen
    e.particleBirthRate = 200; e.particleLifetime = 1.2
    e.emissionAngleRange = .pi * 2; e.particleSpeed = 180; e.yAcceleration = -300
    if UIAccessibility.isReduceMotionEnabled { e.numParticlesToEmit = 12; e.particleSpeed = 40 }
    return e
}
```

**9-slice / stretchable UI** — one small asset scales to any width; corners stay crisp:
```swift
let btn = SKSpriteNode(texture: SKTexture(imageNamed: "btn_primary"))
btn.centerRect = CGRect(x: 12/48.0, y: 12/24.0, width: 24/48.0, height: 1/24.0)   // normalized
btn.size = CGSize(width: targetWidth, height: 48)
// SwiftUI equivalent: Image("btn_primary").resizable(capInsets: .init(top:12,leading:12,bottom:12,trailing:12))
```
Spec cap insets in the atlas JSON. **Export sizes:** author @2x/@3x (single-scale PDF/SVG for flat
art); keep each atlas page within the texture budget (treat 2048²/4096² as the ceiling) and split
actors across atlases rather than over-packing one page.

---

## 4. Light 3D (only when the design needs depth)

Default stays 2D; reach for 3D for a 2.5D parallax scene, a spinning collectible, a prop on a board,
a tappable trophy. Apple-first: **SceneKit** (`SCNScene`/`SCNView`, node mind-set) or **RealityKit**
(`RealityView`), in a SwiftUI shell via `SceneView` / `RealityView`. **CAN** author scene-graph code,
**procedural meshes** (`SCNBox`/`SCNSphere`/`SCNCylinder`/`SCNPyramid`/`SCNTorus` or raw
`SCNGeometry`), PBR materials, lighting/camera rigs, and **written USDZ specs**. **CANNOT** sculpt
organic meshes or bake a `.usdz` from nothing — use a 3D-gen MCP tool when connected, else deliver
geometry code + spec and say so plainly. Never fabricate a "finished `.usdz`."

```swift
import SceneKit
func makeCoin() -> SCNNode {                              // flat gold collectible, no asset file
    let coin = SCNCylinder(radius: 0.5, height: 0.08)     // metres; thin disc
    coin.radialSegmentCount = 48                          // smooth rim, low tri count
    let gold = SCNMaterial(); gold.lightingModel = .physicallyBased
    gold.diffuse.contents = UIColor(red: 0.98, green: 0.78, blue: 0.20, alpha: 1)  // not color-alone:
    gold.metalness.contents = 0.9; gold.roughness.contents = 0.25                   // shape+shine read too
    coin.materials = [gold]
    let node = SCNNode(geometry: coin); node.eulerAngles.x = .pi / 2
    node.runAction(.repeatForever(.rotateBy(x: 0, y: .pi*2, z: 0, duration: 2)))    // swap for static under Reduce Motion
    node.accessibilityLabel = "Gold coin"                 // a11y on the 3D node
    return node
}
```

**USDZ build spec** (hand to a 3D-gen tool or artist; never faked):
```yaml
asset: treasure_chest.usdz
units: meters                 # USDZ is real-scale; author at gameplay size
bounds: 0.40 x 0.30 x 0.28
pivot: base-center (0,0,0), +Y up, -Z forward
triangles: <= 1500            # mobile prop budget
materials:
  body: { type: PBR, baseColor: "#8A5A2B", roughness: 0.6, metalness: 0.0 }
  trim: { type: PBR, baseColor: "#E8B824", roughness: 0.3, metalness: 0.8 }
textures: 1024px max, sRGB albedo + linear normal, power-of-two
contains: no audio, no links, no logos/brands/characters   # original + kids-safe
provenance: generated by <tool/prompt> OR user-owned — record source + licence
import: SCNScene(named:"treasure_chest.usdz") / try Entity.load(named:)
```
**Budget (mobile-first):** props few-hundred → ~1–2k tris; whole 2.5D scene well under a few-hundred
draw calls; share materials so the renderer batches; textures ≤1024px (2048 only if truly needed),
power-of-two. One key light + ambient; bake/disable real-time shadows on old devices. **Pause the
renderer on static/menu screens.** Honor Reduce Motion. Verify with the SceneKit statistics HUD
(`scnView.showsStatistics = true`); profile on the oldest device and report **real** numbers.

---

## 5. Palette, art direction & licensing

**Pick one harmony, name roles semantically** (not appearance), so the palette survives a recolor:
```swift
enum Palette {
    static let paper  = Color(hex: 0xFFF8E7)  // background
    static let ink    = Color(hex: 0x1A2238)  // primary text / outlines
    static let grass  = Color(hex: 0x2E7D32)  // "go" / correct
    static let tomato  = Color(hex: 0xE5484D) // "stop" / wrong
    static let accent = Color(hex: 0xF4A340)  // selection / focus
}
```

**Gate contrast against WCAG AA (build-failing).** Compute every figure/ground pair; require
**4.5:1** body text, **3:1** large text / graphics / UI affordances. Report the real numbers; **fail
and fix** low pairs:
```swift
// ink #1A2238 on paper #FFF8E7 → 14.9:1  PASS (text)
// white     on grass #2E7D32  → 5.13:1  PASS (text)
// white     on tomato #E5484D → 3.91:1  FAIL text (needs 4.5) / PASS graphic (3.0)
//   → fix: darken tomato to #C62828, or use white only for large glyphs/icons on it
func contrastRatio(_ a: Color, _ b: Color) -> Double   // relative luminance, WCAG 2.x
```

**Never color alone.** Every meaningful color gets a redundant channel — this single rule makes the
game work for color-blind and screen-reader players at once:
```swift
struct Token { let color: Color; let symbol: String; let label: String }
let correct = Token(color: .grass,  symbol: "checkmark.circle.fill", label: "Correct")
let wrong   = Token(color: .tomato, symbol: "xmark.circle.fill",     label: "Try again")
// pairs with .accessibilityLabel(token.label) on the control
```

**Color-blind check.** Transform the palette through protanopia/deuteranopia/tritanopia matrices and
flag any pair whose simulated hues collapse (classic red/green). Fix with **value or shape**
separation, not a different hue.

**Art-direction one-pager** (`assets/art-direction.md`) for humans + downstream agents:
```markdown
# Art Direction — Forest Match (placeholder)
Mood: friendly, calm, no-fail.   Harmony: analogous warm + 1 accent.
Shapes: rounded; corner radius 12; line weight 3pt; no sharp spikes.
Motion: gentle ease; honor Reduce Motion (swap motion for fades).
Color rule: never color alone — pair with SF Symbol + label.
Don't: scary faces, brand logos, real text baked into images, hot/flashing colors.
```

**Licensing gate (the hard line).** **Reject** copyrighted characters, logos, brand/licensed fonts,
sprite rips, licensed music/SFX, "inspired-by" mascots, recognizable IP, celebrity likeness.
**Allow** only (a) original/placeholder art the agent generates, (b) **SF Symbols** within Apple's
terms, (c) assets the user **explicitly owns** (confirm first). **Record everything** in a manifest
for `legal-compliance`, and emit a NOTICE entry for any user-supplied third-party-licensed asset:
```json
{ "assets": [
  { "path": "Resources/Assets.xcassets/tile_leaf", "source": "generated:art-as-code",
    "license": "original-placeholder", "owner": "project", "confirmed": true },
  { "path": "Resources/Audio/sfx_pop.caf", "source": "user-provided",
    "license": "user-owned", "owner": "client", "confirmed": true }
]}
```

---

## Image/3D-gen MCP tools (when connected)
If Figma / Adobe Express / Reality Composer / text-to-3D tools are available, drive them from the
spec to make **net-new, original** art. Then **re-run the same gates** — contrast, color-blind,
kids-safe content, licensing — before the asset enters `Resources/`. When no tool is present, the
art-as-code + spec path is the deliverable, not a stopgap.

## Workflow & handoff
1. Read the need from the GDD / `engine-architect` (what animates, frame count, fps, loop, screen).
2. Define palette + tokens once; report contrast and color-blind results.
3. Write the spec; generate placeholders in code so gameplay runs now.
4. If a gen tool exists, drive it and **verify against the spec**; else ship code/vector + spec.
5. Hand off: art-as-code + tokens → **`gameplay-programmer`**; asset manifest + NOTICE →
   **`legal-compliance`**; contrast + color-blind report + never-color-alone map → **`qa-tester`** /
   a11y review. State what was authored vs. only spec'd, whether an MCP tool produced it, and what
   an artist must still draw. **No App Store / licensing compliance guarantee** — checklist + risk
   list only.

## Quick self-check
- [ ] Every asset is generated/original/confirmed-owned; manifest + NOTICE recorded.
- [ ] Cheapest medium chosen (Shape/Canvas before SVG before raster/3D).
- [ ] Vector where possible; PDF marked Preserve Vector Data / Single Scale.
- [ ] Generative/3D art deterministic via injected seed; snapshot/geometry test added where worth it.
- [ ] Contrast meets WCAG AA and is reported with real numbers; low pairs fixed.
- [ ] Color-blind simulated; meaning never by hue alone (shape + symbol + label).
- [ ] Decorative art `accessibilityHidden`; Reduce Motion honored; Dynamic Type in HUD; 3D nodes labeled.
- [ ] Particles finite & gentle; atlas pages within budget; render loop paused on static screens.
- [ ] Kids-safe imagery; no runtime art fetches / trackers / external links in any bundle.
- [ ] Variants/metadata as data; views/scenes thin; honest note on built vs. spec'd and tool use.