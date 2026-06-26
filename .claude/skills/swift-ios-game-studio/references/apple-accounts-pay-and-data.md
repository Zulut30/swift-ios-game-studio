# Apple accounts, payments & data collection

Account, payment, and data-collection features collide hardest with this skill's kids-safe
defaults. This one reference is the gate before any of them lands in a game. It is engineering
guidance grounded in published rules — **not legal advice, and never a guarantee of App Store, Kids
Category, COPPA, or GDPR-K approval.** Laws and Apple's guidelines change and apply by audience and
region; verify the final design against the current App Store Review Guidelines and with qualified
counsel before shipping.

## The default: collect nothing, sell nothing, no accounts

For the simple, kids-first 2D games this skill builds, the honest default is **none of these
features**: no Sign in with Apple, no Apple Pay, no StoreKit IAP, no data collection beyond local
progress/settings. A game stores its state on-device (`UserDefaults` / a `Codable` file), runs
offline, and needs no login, no payment, and no identity. Add a feature below **only** with a
written reason — and in a kids context, never in the child-facing flow.

## Decide the audience first

Every rule branches on who the app is for. Pick the strictest applicable bar.

- **Kids build** — the app is in the **Kids Category**, OR is primarily directed to children
  **under 13** (COPPA's line; GDPR-K sets the digital-consent age at **13–16** by EU member state),
  OR you reasonably expect a child audience. **Mixed-audience apps that knowingly serve children
  inherit the kids bar for those users.** When the audience is unspecified, this skill assumes the
  **kids build** — and ships none of the four features.
- **General build (13+)** — a general-audience game **not** in the Kids Category, with no
  child-directed framing. A general build may add these features, but only with a real need, a
  neutral **age gate** to branch child users onto the kids-safe path, **parental gates** on
  commerce, and a privacy manifest + App Privacy label that match what the code actually does.

### Age gate vs. parental gate vs. verifiable parental consent — don't conflate them

- **Age gate** — a neutral birthdate/age entry that *branches* the experience (kids path vs. 13+
  path). Must be **non-incentivized** and not pre-filled to an adult age. Collect the minimum
  (often just an age band); don't persist a birthdate you don't need. It is **not** identity
  verification and **not** parental consent.
- **Parental gate** — a deliberate-action challenge a young child can't pass by accident (e.g.
  "type the number written as words", multi-digit math, press-and-hold). Gate **purchases,
  external links, and anything that leaves the play space** behind it. It limits accidental access;
  it is **not** verifiable parental consent.
- **Verifiable parental consent (VPC)** — what COPPA actually requires *before* collecting a
  child's personal data. A parental gate is **not** VPC, and a tappable "I'm over 13" box is not
  verification. If a kids build would collect any personal data, stop: redesign to collect none, or
  get counsel plus a real VPC mechanism. **Default: collect none.**

## Sign in with Apple

Sign in with Apple (the `AuthenticationServices` framework) is the privacy-preserving way to add an
account. **You rarely need it.** A simple game stores progress locally and needs no login. Add it
only when accounts are genuinely required (cross-device save via your own backend, a shared
profile). The moment you offer **any other third-party or social login** (Google, Facebook, your
own email/password), App Store Review Guideline 4.8 requires you to **also** offer an equivalent
login that limits data to name + email and lets the user keep the email private — in practice, Sign
in with Apple. So if you ship Google/Facebook login, you almost certainly must ship this too, and at
least as prominently.

**Kids:** accounts are generally **not appropriate** for an under-13 / Kids Category experience.
The privacy-first default is **no login in the child-facing flow**. If an app has both kids and
adult audiences, keep any sign-in **behind a parental gate** and out of the kids surface.

### Setup

- **Entitlement.** Add the **Sign in with Apple** capability in Xcode, which writes
  `com.apple.developer.applesignin` (value `Default`) into your `*.entitlements` and registers it on
  your App ID. Without it the request fails at runtime.
- **No Info.plist usage string** is required for Sign in with Apple itself.
- **Email relay (optional).** If your backend sends mail, configure Apple's private email relay so
  mail to the `@privaterelay.appleid.com` address is delivered.

### Exactly what data you receive

- **Stable user identifier** (`credential.user`) — an opaque string, **stable per Apple ID per app
  team**, returned on every sign-in. This is your durable key; persist it in the **Keychain** and
  look the user up by it. It is not an email and not a device ID.
- **Full name and email — ONCE, on the first authorization only.** `credential.fullName` and
  `credential.email` are populated **only the first time** a given Apple ID authorizes your app; on
  every later sign-in they are `nil`. **Capture and store them on first auth** (or re-fetch from
  your server) — there is no API to ask Apple again. Re-prompting requires the user to revoke the
  app in Settings first.
- **Private email relay.** If the user chose "Hide My Email," `credential.email` is an
  `@privaterelay.appleid.com` relay address. Treat it as the real address for delivery; never try to
  de-anonymize it.
- **Identity token + authorization code.** `credential.identityToken` (a signed JWT) and
  `credential.authorizationCode` are for your **server** to verify the sign-in. Do not trust the
  client-side `user` string alone for anything security-sensitive — verify the token server-side.

### Request flow

`ASAuthorizationAppleIDProvider` builds the request; `ASAuthorizationController` runs it. Request
**only the scopes you actually use** — prefer `[.fullName]` or `[]` over `.email` if you don't send
mail. The delegate is callback-based; wrap it in `withCheckedThrowingContinuation` for async/await,
and treat `ASAuthorizationError.canceled` as a normal user cancel (no failure UI). See
`assets/apple-signin-iap-template.swift` for a complete coordinator, plus reading the one-time
fields on first auth and storing the `user` identifier in the Keychain.

### SwiftUI button

`SignInWithAppleButton` (from `AuthenticationServices`/SwiftUI) renders Apple's compliant button —
**use it**; do not draw your own or relabel it. It must be at least as prominent as any other login
option (Guideline 4.8).

```swift
import SwiftUI
import AuthenticationServices

SignInWithAppleButton(.signIn) { request in
    request.requestedScopes = [.fullName, .email]   // request ONLY what the feature needs
} onCompletion: { result in
    switch result {
    case .success(let auth):
        if let c = auth.credential as? ASAuthorizationAppleIDCredential {
            // capture c.user / c.fullName / c.email on FIRST auth; verify c.identityToken server-side
        }
    case .failure:
        break   // ASAuthorizationError.canceled is a normal cancel
    }
}
.signInWithAppleButtonStyle(.black)   // .black / .white / .whiteOutline — match your UI
.frame(height: 44)                    // honor min touch target; respects Dynamic Type
```

### Verifying the credential & handling revocation (required)

The user can revoke your app under **Settings → [Apple ID] → Sign in with Apple**. You must react
on two paths:

- **Re-check `credentialState(forUserID:)` on launch** to catch revocations that happened while the
  app was closed. Handle `.revoked` / `.notFound` by signing the user out locally.
- **Observe `ASAuthorizationAppleIDProvider.credentialRevokedNotification`** while running and sign
  out when it fires.
- If you have a server with refresh tokens, honor Apple's **server-to-server revocation
  notifications** so the backend deletes its copy.

The template implements both client paths. Handle `.transferred` (app moved between dev teams) per
your backend.

### Storing the credential — Keychain, not UserDefaults

The stable `user` identifier is the durable key; keep it in the **Keychain**
(`kSecClassGenericPassword`, `kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly`), not
`UserDefaults` (which is unencrypted and backed up). Store only what you need; **never log tokens.**

### Account deletion & privacy posture

- **In-app account deletion.** If you support account creation, Guideline 5.1.1(v) requires in-app
  account deletion that also deletes server-side data. Revocation must delete the backend copy too.
- **Don't track.** Sign in with Apple is identity, not analytics. Do not pair it with IDFA/ATT,
  fingerprinting, or third-party analytics SDKs. Adding an account does **not** license data
  collection.
- **Update `PrivacyInfo.xcprivacy` honestly.** Once you collect a user ID / name / email, the
  "collects nothing" manifest is no longer accurate — add the matching `NSPrivacyCollectedDataTypes`
  entries (user ID, name, email address) and keep `NSPrivacyTracking` `false` only if you genuinely
  don't track. Request the narrowest scopes; store the relay email; delete server-side data on
  revocation and on account-deletion request.

## Apple Pay (PassKit) vs. StoreKit 2 — pick the right one

These are two different payment systems with non-overlapping use cases. Picking the wrong one is a
guaranteed rejection, so decide first.

| Use case | Framework | API surface |
|---|---|---|
| **Digital** content/features inside the app: unlock levels, remove ads, cosmetics, coins, subscriptions, "pro" mode | **StoreKit 2** (required by Apple) | `Product`, `Product.PurchaseResult`, `Transaction`, `Transaction.currentEntitlements` |
| **Physical** goods/services delivered outside the app: real merch, event tickets, food delivery, a physical book | **Apple Pay** via **PassKit** | `PKPaymentAuthorizationController`, `PKPaymentRequest`, `PKMerchantCapability` |

Apple's rule (App Store Review Guidelines §3.1.1): unlocking features or digital content **must** use
In-App Purchase (StoreKit). **Apple Pay is not allowed for digital content.** Conversely, you **may
not** sell physical goods through IAP — those go through Apple Pay or another payment method, and
Apple takes no commission. If the thing the user buys never leaves the app, it's StoreKit. If it's a
real-world object or service, it's Apple Pay.

### StoreKit 2 — digital in-app purchases (async/await)

StoreKit 2 (iOS 15+) replaces the old `SKPaymentQueue`/receipt-file flow. Transactions are JWS-signed
by Apple and verified on-device via `VerificationResult`; you rarely need a server. The template
(`assets/apple-signin-iap-template.swift`) ships a complete `Store` with product loading, a
launch-time `Transaction.updates` listener, verified purchase handling, restore, and entitlement
refresh. Key points:

- **Verification is mandatory.** `product.purchase()` and the `Transaction.*` sequences yield
  `VerificationResult` (`.verified` / `.unverified`). Grant entitlements **only** on `.verified`;
  treat `.unverified` as "did not happen," and never call `unsafePayloadValue` to bypass it.
- **`Transaction.currentEntitlements`** is the on-device receipt: iterate it at launch to restore
  non-consumables/subscriptions. Pair it with a **"Restore Purchases"** button that calls
  `try await AppStore.sync()` (required for non-consumables).
- **`Transaction.updates`** must have a listener running from launch, or you'll miss Ask to Buy
  approvals, Family-Sharing grants, renewals, and refunds (`revocationDate` set).
- **Call `transaction.finish()`** once content is delivered, or StoreKit keeps redelivering it.
- **Test with a `.storekit` configuration file** in the scheme — no sandbox account needed; add
  `import StoreKitTest` for `SKTestSession` unit tests.
- **Server-side validation** (App Store Server API / `Transaction.jsonRepresentation` → your
  backend) is optional but recommended if entitlements are valuable enough to spoof. A kids-first
  offline game generally should not run a backend at all.

**Ask to Buy & Family Sharing.** Ask to Buy (a Screen Time / Family Sharing parental control)
returns `Product.PurchaseResult.pending`; the purchase completes later via `Transaction.updates` when
a parent approves — your UI must handle "pending" gracefully (no spinner forever, no re-prompting).
Mark eligible products Family Shareable in App Store Connect; shared entitlements arrive through
`Transaction.updates`/`currentEntitlements`. You **cannot** detect or bypass these controls — design
for the pending/late-grant path.

### Apple Pay (PassKit) — physical goods only

Requires a Merchant ID and the **Apple Pay** capability/entitlement
(`com.apple.developer.in-app-payments`) in the app's `.entitlements`. Use only for real-world
goods/services — rare in a simple 2D game.

```swift
import PassKit

func payForPhysicalOrder() {
    let request = PKPaymentRequest()
    request.merchantIdentifier = "merchant.com.example.game"
    request.supportedNetworks = [.visa, .masterCard, .amex]
    request.merchantCapabilities = .threeDSecure
    request.countryCode = "US"
    request.currencyCode = "USD"
    request.paymentSummaryItems = [
        PKPaymentSummaryItem(label: "Plush toy", amount: NSDecimalNumber(string: "19.99")),
        PKPaymentSummaryItem(label: "My Game Store", amount: NSDecimalNumber(string: "19.99")),
    ]
    let controller = PKPaymentAuthorizationController(paymentRequest: request)
    controller.delegate = self   // implement PKPaymentAuthorizationControllerDelegate
    controller.present(completion: nil)
}
```

In the delegate, send the encrypted `PKPayment.token` to your payment processor (Stripe, Braintree,
your own), then call the completion handler with `.success`/`.failure`. Apple Pay is **not** for
digital unlocks — App Review will reject that.

### Kids, parental gates & dark patterns

- **Behind a parental gate, always.** In any app for or likely used by children, *every* path to a
  purchase (the store screen, "Buy", "Restore", Apple Pay) must sit behind a parental gate, and the
  store UI must not be reachable from normal play.
- **The Kids Category is the strictest tier.** Apple imposes extra limits on the Kids Category (and
  under-13 audiences under COPPA/GDPR-K); IAP and third-party commerce here face additional scrutiny
  and may be restricted or disallowed. Many kids titles ship **no IAP**. Do not assume an
  IAP/Apple Pay design will pass — verify against the current guidelines before building it.
- **No purchase pressure / no dark patterns.** No countdown timers, fake scarcity, "your friends
  bought this", pestering pop-ups, soft-currency confusion that obscures real cost, loot boxes
  without disclosed odds, or a "continue" button that triggers a charge. Disclose real prices in
  real currency.
- **Disclose honestly.** Declare IAP on the App Store product page; keep `PrivacyInfo.xcprivacy`
  accurate (**purchase history** is a data type — receipt/IAP data sent off-device must be declared,
  and tracking stays `NSPrivacyTracking=false` for a privacy-first kids app).

## What data you may legally collect

For these games the safe default is **collect nothing**: on-device, anonymous, offline-first.
Collect personal data only with a written reason, the right consent, and an honest privacy manifest.

### Two principles that decide everything

- **Data minimization.** Collect the least data needed for the feature to work — ideally none. If a
  mechanic works on-device, keep it on-device.
- **Purpose limitation.** Use data only for the specific purpose you disclosed. Don't quietly reuse
  "save progress" data for analytics, ads, or profiling. A new purpose needs new disclosure/consent.

### Consent, and who can give it

- **Under-13 (US, COPPA):** collecting personal information from a child under 13 requires
  **verifiable parental consent** *before* collection. A child cannot consent for themselves.
- **EU/EEA (GDPR-K):** the age of digital consent is **13–16 depending on the member state**; below
  it, a parent/guardian must consent. Treat 16 as the conservative threshold unless you've confirmed
  the country.
- **Apple Kids Category:** apps in (or targeting) the Kids Category must **not** include third-party
  analytics or advertising, must get verifiable parental consent before any data collection, and
  must gate links out of the app behind a parental gate. This skill's default — no SDKs, no
  accounts, no network — sidesteps most of this surface.

### App Privacy "nutrition label" (App Store Connect)

Separate from the manifest, App Store Connect asks you to declare, per data type, whether it is
**collected**, **linked to identity**, and **used for tracking** (Contact Info, Health, Financial,
Location, Sensitive Info, Contacts, User Content, Browsing/Search History, Identifiers, Purchases,
Usage Data, Diagnostics). The honest answer for a privacy-first kids game is **"Data Not
Collected."** Declaring that obligates you to actually collect nothing — keep the code matching the
label.

### PrivacyInfo.xcprivacy + required-reason APIs

The privacy manifest (`PrivacyInfo.xcprivacy`, an Apple plist) declares tracking, tracking domains,
collected data types, and **required-reason API** usage. See `assets/PrivacyInfo.xcprivacy` for the
collects-nothing template. Key truths:

- Even an app that collects no *personal* data often calls a **required-reason API** and must list
  it with an **approved reason code** under `NSPrivacyAccessedAPITypes`. Common categories:
  `NSPrivacyAccessedAPICategoryUserDefaults` (e.g. saving settings — reason `CA92.1`),
  `…FileTimestamp` (`C617.1`), `…DiskSpace`, `…SystemBootTime`, `…ActiveKeyboards`. Using the API
  *on-device for your own app* is fine — you just declare the reason. Saving high scores in
  `UserDefaults` is local persistence, **not** "data collection."
- Keep `NSPrivacyTracking` `<false/>` and `NSPrivacyTrackingDomains` empty unless tracking is real
  and consented (and never for kids).

### ATT / IDFA — opt-in, and prohibited for kids

The advertising identifier (IDFA, `ASIdentifierManager.advertisingIdentifier`) and cross-app/site
tracking require **App Tracking Transparency** — the user must opt in via
`ATTrackingManager.requestTrackingAuthorization`, and you may only track after `.authorized`. **For
children's apps this is off the table:** don't import `AppTrackingTransparency`/`AdSupport`, don't
call the request, and don't ship `NSUserTrackingUsageDescription`. No IDFA, no tracking SDKs, no
fingerprinting.

```swift
// ATT is opt-in and must NOT appear in a kids app. Shown only to illustrate the gate a
// general-audience app would respect — a privacy-first kids game ships none of this.
import AppTrackingTransparency

let status = await ATTrackingManager.requestTrackingAuthorization()
guard status == .authorized else {
    return  // no tracking, no IDFA — run fully featured without it
}
```

### What you can do WITHOUT collecting personal data

Most of what feels like "data" needs no collection at all:

- **On-device only.** Progress, settings, and high scores in `UserDefaults` or a `Codable` file in
  the app sandbox. It never leaves the device, so it isn't "collected" in the regulatory sense
  (still declare the required-reason API).
- **Anonymous / no identifiers.** Don't mint or store a user ID, don't read device IDs, don't ask
  for name/email/birthday. A game can be fully featured with zero identity.
- **Aggregated & on-device.** For product insight, prefer **MetricKit** / on-device diagnostics the
  user controls over any phone-home analytics SDK. Aggregate locally; ship nothing that
  re-identifies a person.
- **Offline-first.** Network off by default removes most collection risk outright. If the game truly
  needs the network, document why and keep payloads free of personal data.

```swift
// Local, anonymous high-score persistence — no account, no network, no identifier.
struct ScoreStore {
    private let defaults = UserDefaults.standard          // required-reason API: declare CA92.1
    private let key = "bestTimeSeconds.level1"

    func best() -> Double? {
        defaults.object(forKey: key) as? Double           // nil until first win
    }
    func record(_ seconds: Double) {
        guard best().map({ seconds < $0 }) ?? true else { return }
        defaults.set(seconds, forKey: key)                // stays on device
    }
}
```

## Decision matrix

This matrix is the gate before any of the four features ships. Same caveats as above — operational
guidance, **not** legal advice or a compliance guarantee.

| Feature | Kids build (Kids Category / <13) | General build (13+) | Gating required when allowed |
|---|---|---|---|
| **Sign in with Apple** (`AuthenticationServices`) | **PROHIBITED** in the child-facing flow. An account implies an identifier + data. Default: **no accounts.** | **ALLOWED** only if the game genuinely needs an account. If you offer *any* third-party social login, SiwA is generally **required** alongside it (§4.8). | Account is optional (never gates core play). Disclose the stored user ID / optional name / email-relay in the manifest + App Privacy label. |
| **Apple Pay** (`PassKit`) | **PROHIBITED** in the child-facing flow. Apple Pay is for **physical** goods; digital content via Apple Pay violates §3.1.1. | **RESTRICTED**: real-world physical goods/services only — **never** digital content/currency (that's StoreKit IAP). Rare in a simple game. | Entire purchase entry point behind a **parental gate**. Disclose any payment/contact/shipping data. |
| **StoreKit IAP** (`StoreKit`) | **RESTRICTED → effectively PROHIBITED for under-13 by default.** If monetization exists, the flow **must** sit behind a parental gate; no manipulative design; loot-box odds disclosed (§3.1.1). Many kids titles ship **no IAP**. | **ALLOWED** — the only sanctioned way to sell digital content/subscriptions. Use **StoreKit 2** and verify transactions (`.verified` only). | No dark patterns / fake urgency / nag screens. For kids: parental gate before the store; restore-purchases path; honest pricing. |
| **Any data collection** (analytics, IDs, contact, location, UGC, crash logs, "optional" telemetry) | **PROHIBITED by default.** No third-party analytics, no IDFA/ATT, no fingerprinting, no PII. Store only **local** progress/settings. | **RESTRICTED**: permitted **with** an accurate App Privacy label + `PrivacyInfo.xcprivacy`, data minimization, and a lawful basis/consent. ATT prompt only if you actually track. | Neutral age gate before any 13+-only data path; honest manifest; ATT only where tracking truly occurs; never collect from a user the gate identified as a child. |

**Bottom line:** *kids games = none of the four.* Keep scores/progress local, no accounts, no
payments, no telemetry, offline-first. *General games* may add them **only** with a real need, a
neutral age gate, parental gates on commerce, StoreKit (not Apple Pay) for digital goods, and a
privacy manifest + App Privacy label that **matches what the code actually does**.

## Consolidated checklist

- [ ] **Audience declared** in the Mini-GDD (kids build vs. general build). Unspecified ⇒ kids
      default: none of the four features.
- [ ] **Kids build has none of the four:** no `AuthenticationServices`/Sign in with Apple, no
      `PassKit`/Apple Pay, no `StoreKit` IAP, no data collection beyond local progress/settings.
- [ ] No accounts/login gate the core kids experience; core play works fully offline.
- [ ] **Accounts actually needed** before adding Sign in with Apple — a local save was ruled out
      first; no login added "just in case."
- [ ] If any other third-party/social login is offered, Sign in with Apple is **also** offered and
      at least as prominent (Guideline 4.8); Apple's `SignInWithAppleButton` is used (correct
      label/style, ≥44pt, Dynamic Type) — no hand-drawn or relabeled button.
- [ ] Only the scopes actually used are requested (`[.fullName]`/`[]` over `.email` when no mail is
      sent); `fullName`/`email` captured and persisted on the **first** authorization.
- [ ] Hide-My-Email relay treated as the delivery address; no attempt to de-anonymize.
- [ ] `identityToken`/`authorizationCode` verified **server-side** before the sign-in is trusted;
      the client `user` string alone is not trusted for security.
- [ ] Stable user identifier stored in the **Keychain** (not UserDefaults); tokens never logged.
- [ ] Revocation handled: `credentialRevokedNotification` observed at runtime **and**
      `credentialState(forUserID:)` re-checked on launch; `.revoked`/`.notFound` signs out.
- [ ] In-app account deletion provided (5.1.1(v)) and deletes server-side data; revocation deletes
      the backend copy.
- [ ] **Digital content/features use StoreKit 2 IAP, never Apple Pay;** Apple Pay (if any) is
      physical goods/services delivered outside the app only.
- [ ] StoreKit: entitlements granted only on `.verified` (`.unverified` ignored, never
      `unsafePayloadValue`); a `Transaction.updates` listener runs from launch; `currentEntitlements`
      read at launch; a Restore button calls `AppStore.sync()`; each delivered transaction calls
      `finish()`; `pending` (Ask to Buy) handled without a stuck UI or re-prompting.
- [ ] Apple Pay entitlement (`com.apple.developer.in-app-payments`) / Merchant IDs appear **only** in
      a general build that intentionally sells physical goods.
- [ ] In a kids/children's app, **every** purchase path (store, Buy, Restore, Apple Pay) sits behind
      a parental gate and is unreachable from normal play.
- [ ] No purchase-pressure dark patterns: no fake urgency/scarcity, no loot boxes without disclosed
      odds, no currency obfuscation, no purchase-triggering "continue" buttons; real prices in real
      currency, disclosed on the product page.
- [ ] Kids Category / under-13 IAP design checked against the **current** App Store Review Guidelines
      before building; no assumption of approval.
- [ ] **Default data posture is collect-nothing:** on-device, anonymous, offline-first; App Privacy
      label set to **"Data Not Collected"** and the code actually collects nothing.
- [ ] `PrivacyInfo.xcprivacy` present and honest: `NSPrivacyTracking=false`, empty
      `NSPrivacyTrackingDomains`; `NSPrivacyCollectedDataTypes` empty for a kids game, or accurately
      listing any user ID/name/email/purchase-history now collected.
- [ ] Every required-reason API used (UserDefaults, file timestamps, disk space, system boot time,
      active keyboards) is declared under `NSPrivacyAccessedAPITypes` with an approved reason code.
- [ ] **No** `AppTrackingTransparency`/`AdSupport`, no IDFA, no `NSUserTrackingUsageDescription`, no
      tracking/analytics SDKs in a kids app; no tracking paired with sign-in or IAP.
- [ ] **Age gate (general build only)** is neutral, non-incentivized, not pre-filled, collects the
      minimum, and branches child users onto the kids-safe path.
- [ ] **No VPC shortcut:** a parental gate is not verifiable parental consent; a kids build that
      would collect personal data is redesigned to collect none, or has a real VPC mechanism.
- [ ] Any personal data collection has a written purpose and the right consent (VPC under 13; parent
      consent below GDPR-K age 13–16) and matching label + manifest.
- [ ] Links out of the app and any data-collecting feature sit behind a parental gate.
- [ ] **Risk list, not a guarantee.** Hand off open compliance risks and "verify with counsel";
      never claim guaranteed Kids Category / App Review / COPPA / GDPR-K approval.