# Haptics & Guided Access

Two feel/safety features that punch above their weight in kids' games: tactile feedback (juice)
and Guided Access (lock the device into your game). Both are optional but cheap to do well.

---

## Haptics — tactile feedback (juice)

Short, meaningful vibrations make taps and wins feel satisfying. Use the simplest API that fits.

### UIFeedbackGenerator — the easy 90%
Built-in, system-tuned haptics for common events. Prepare before firing to cut latency.

```swift
import UIKit

let impact = UIImpactFeedbackGenerator(style: .light)   // .light/.medium/.heavy/.soft/.rigid
impact.prepare()
impact.impactOccurred()                                  // e.g. a card flip, a tap landing

let notify = UINotificationFeedbackGenerator()
notify.notificationOccurred(.success)                    // match found / level won
notify.notificationOccurred(.error)                      // illegal move (use sparingly for kids)

let selection = UISelectionFeedbackGenerator()
selection.selectionChanged()                             // moving through a picker/palette
```
Map haptics to **model events**, not raw touches: success on match/win, light impact on a valid
placement, selection on palette change. Wrap in a tiny `HapticsSystem` so it's mute-able and testable.

### Core Haptics — custom patterns (only if you need them)
`CHHapticEngine` plays designed patterns (intensity/sharpness curves, transient + continuous).
Reach for it only when `UIFeedbackGenerator` can't express the effect (a custom "rumble", a rhythmic
pattern). It's more code and must handle engine start/stop and interruptions.

```swift
import CoreHaptics
// Guard support; many devices/simulator lack the engine.
guard CHHapticEngine.capabilitiesForHardware().supportsHaptics else { return }
let engine = try CHHapticEngine()
try engine.start()
// build CHHapticEvent(s) -> CHHapticPattern -> player; stop the engine when idle.
```

### Rules for haptics
- **Check support** (`CHHapticEngine.capabilitiesForHardware().supportsHaptics`); iPad and the
  simulator often have none — degrade gracefully (no crash, no-op).
- **Respect a Reduce-Motion / settings toggle** and a global mute. Some users find haptics
  unpleasant; make them optional, on by default only if tasteful.
- **Don't overdo it.** Subtle and occasional beats constant buzzing — especially for young kids.
- Prepare generators before use to avoid first-fire latency; stop the Core Haptics engine when idle
  to save battery (see `performance-checklist.md`).
- Keep firing logic out of the hot loop; trigger on discrete model events only.

---

## Guided Access — lock the device into your game (great for kids)

Guided Access is an iOS Accessibility feature a **parent/teacher enables** (Settings ▸ Accessibility
▸ Guided Access, then triple-click the side/home button) to lock the device to a single app and
optionally disable touch areas, the volume buttons, or auto-lock. It's the simplest "kiosk mode"
for toddlers — they can't accidentally exit the game, open Safari, or make purchases.

### What the app should do
- **Detect it** so you can adapt UI (e.g. hide an in-app "exit" that won't work anyway):
  ```swift
  import UIKit
  let isLocked = UIAccessibility.isGuidedAccessEnabled
  NotificationCenter.default.addObserver(forName: UIAccessibility.guidedAccessStatusDidChangeNotification,
                                         object: nil, queue: .main) { _ in
      // update UI for locked/unlocked
  }
  ```
- **Single-App Mode (MDM/Autonomous):** for managed devices, an app can request
  `UIAccessibility.requestGuidedAccessSession(enabled:) { success in }` (requires the app to be
  configured for Autonomous Single App Mode via MDM). Niche — most consumer kids' apps just rely on
  the parent-enabled Guided Access above.

### Why it matters for the skill's audience
- Recommend Guided Access in your app's **parents' section / onboarding** as the safe way to hand a
  device to a small child. It complements the skill's child-safety defaults (no external links, no
  IAP in the kids flow) — Guided Access is the device-level backstop.
- Don't *depend* on it (you can't force it on consumer devices), but **design to be safe with or
  without it**: no destructive actions reachable by a stray tap, no way to leave the play space into
  paid or external content.

### Related accessibility
This pairs with the broader a11y/child-safety rules in `accessibility-child-safety.md`
(VoiceOver, Dynamic Type, Reduce Motion, parental gates, privacy). Guided Access is the
"keep them in the sandbox" piece; those are the "make the sandbox usable and safe" pieces.
