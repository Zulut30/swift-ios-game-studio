# Performance checklist

Simple 2D games should hold a steady frame rate on the oldest supported device with low
battery and thermal impact. Budget first, optimize only what a profiler proves.

## Frame budget
- Target 60 fps → **~16.6 ms/frame** (120 Hz ProMotion → ~8.3 ms). Stay well under.
- Make updates **frame-rate independent**: advance by `dt`, never by "per frame" constants.
- Clamp `dt` (e.g. ≤ 1/30) so a stall doesn't teleport objects.

## SpriteKit specifics
- **Node count:** keep it low; remove off-screen nodes. Watch the live counts via
  `view.showsNodeCount` and `view.showsFPS` during development.
- **Draw count:** minimize draw calls. Use `SKTextureAtlas` so same-atlas sprites batch.
  Use `.ignoresSiblingOrder` and let z-position (not add-order) decide layering.
- **Object pooling:** for runners/spawners, recycle obstacle/coin nodes instead of
  create/destroy churn (which causes GC-like hitches and fragmentation).
- **Physics:** simple bodies (rect/circle), small `physicsWorld` contact set, sleep idle bodies.
  Avoid per-pixel `SKPhysicsBody(texture:)` for many nodes.
- **Actions:** reuse `SKAction`s (they're immutable & shareable); avoid building new actions
  every frame. Prefer actions over manual per-frame mutation when possible.
- **Particles:** cap birthrate and lifetime; stop emitters when done; they're expensive.

## SwiftUI specifics
- Avoid per-frame `@State` thrash. For static/turn-based games, drive with discrete state +
  `withAnimation`, not a continuous loop.
- If you need frames, use `TimelineView(.animation)` / `Canvas` rather than a timer mutating
  many views. Keep the view body cheap; precompute outside `body`.
- Keep view identity stable (`id`) so SwiftUI diffing doesn't rebuild whole subtrees.
- Don't allocate in hot paths; hoist formatters, paths, and gradients out of `body`.

## Memory
- Vector/placeholder art keeps texture memory tiny. For real images, right-size them; don't
  load 4K textures for thumbnail-sized sprites.
- Break retain cycles: scenes ↔ controllers, closures capturing `self` (`[weak self]`).
- Release levels/atlases you're done with; don't keep every level resident.

## Battery & thermals
- Don't run a render loop on a static screen (menu, paused) — pause the scene.
- Lower update frequency when nothing moves; stop audio engines when silent.
- Avoid busy-wait timers; use the display link / SpriteKit loop, not tight polling.

## Loading & launch
- Keep launch fast: defer non-essential work; show the first interactive screen quickly.
- Decode level JSON lazily/per-level; cache parsed levels if revisited.

## How to verify (don't guess)
- Enable `showsFPS`, `showsNodeCount`, `showsDrawCount` in debug builds.
- Use Instruments: **Time Profiler** (CPU), **Allocations/Leaks** (memory), **Animation Hitches**
  / Core Animation FPS, and the **Energy** gauge for battery.
- Test on the **oldest supported device**, not just the newest simulator.

## Quick checklist
- [ ] Updates use `dt`; `dt` is clamped.
- [ ] Steady target fps on the oldest device, no hitches in normal play.
- [ ] Node/draw counts bounded; off-screen nodes removed; pools used for spawners.
- [ ] Textures atlased & right-sized; no oversized images.
- [ ] No render loop on static/paused screens; audio stops when idle.
- [ ] No retain cycles; memory stable over a long session.
- [ ] Verified with Instruments, not assumed.
