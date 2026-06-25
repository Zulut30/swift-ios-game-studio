# Accessibility & child safety

Two intertwined concerns for these games: make them usable by everyone, and make them safe
and private for children. Treat both as requirements, not extras.

## Accessibility (iOS APIs)
- **Labels / values / traits.** Every interactive element gets an accessibility label, and a
  value/trait where meaningful.
  ```swift
  cardView
    .accessibilityLabel("Card")
    .accessibilityValue(card.isFaceUp ? card.symbolName : "face down")
    .accessibilityAddTraits(.isButton)
  ```
- **Don't rely on color alone.** Pair color with shape, symbol, or label (helps color-blind users
  and matching games). Maintain strong contrast (aim WCAG AA: 4.5:1 text, 3:1 large/graphics).
- **Dynamic Type.** Use text styles (`.font(.title)`, `.body`) and avoid fixed point sizes for UI
  text. Verify layouts at the largest accessibility sizes.
- **Reduce Motion.** Check `UIAccessibility.isReduceMotionEnabled` (or
  `@Environment(\.accessibilityReduceMotion)`) and replace large motion/parallax with fades.
- **VoiceOver.** Ensure a logical focus order; group decorative nodes as `.accessibilityHidden(true)`;
  announce key state changes with `.accessibilityHidden`/notifications where helpful.
- **Touch targets.** Minimum ~44×44 pt; larger for young children. Generous spacing prevents mis-taps.
- **No timing-only challenges** for accessibility modes — offer a relaxed/no-timer option.
- **Captions/alternatives** for any essential audio cue (also show it visually).

## Child safety & privacy (privacy-first defaults)
For any app aimed at or likely used by children, default to the strictest, simplest posture:
- **No third-party analytics or tracking.** No IDFA, no App Tracking Transparency prompt,
  no fingerprinting, no SDKs that phone home.
- **No ads** (and certainly no behavioral/targeted ads).
- **No external links** out of the app — no web views to arbitrary URLs, no "rate us" deep links,
  no social sharing that leaves the sandbox. If a parents' section is needed, gate it.
- **No data collection.** Don't collect names, emails, location, contacts, photos, or device IDs.
  Store only local game progress/settings.
- **No accounts / no login** for the core kids experience. No sign-in walls.
- **Minimal permissions.** Request nothing you don't strictly need. No camera/mic/location/contacts
  unless the core mechanic requires it and a parent enables it.
- **No dark patterns.** No fake urgency, no nagging, no manipulative IAP, no loot-box pressure,
  no "tap here to continue" that triggers purchases.
- **No in-app purchases or links to purchases** in the child-facing flow; if monetization exists,
  put it behind a parental gate.
- **Parental gate** for anything sensitive (settings that leave the play space, external links,
  purchases): a simple challenge a young child can't pass by accident.
- **Network off by default.** Offline-first. If the game truly needs the network, document why and
  keep it free of personal data.

## Apple Kids Category awareness (no guarantees)
Apple's Kids Category and applicable laws (e.g. COPPA/GDPR-K) impose strict rules on data,
ads, and external links. This skill helps you *avoid common violations* but **cannot guarantee
approval**. Produce a checklist and a risk list; recommend the user review current
App Store Review Guidelines and consult legal counsel for compliance.

## Quick self-check
- [ ] Every control has an accessibility label/value/trait.
- [ ] Playable without reading text and without relying on color alone.
- [ ] Honors Dynamic Type and Reduce Motion.
- [ ] No tracking, ads, analytics, external links, or accounts in the kids flow.
- [ ] Collects no personal data; stores only local progress/settings.
- [ ] Requests no unnecessary permissions; network off by default.
- [ ] Sensitive actions sit behind a parental gate.
