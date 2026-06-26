//
//  AppleSignInStore.swift  (template)
//  Swift iOS Game Studio — Sign in with Apple + StoreKit 2 starter
//
//  A compact, optional account + in-app-purchase layer for a GENERAL-AUDIENCE (13+) build.
//  Do NOT ship this in a kids / Kids Category / under-13 app: accounts and IAP belong out of
//  the child-facing flow, and any purchase entry point must sit behind a parental gate.
//  See references/apple-accounts-pay-and-data.md before adopting either feature.
//
//  Both features are independent — keep only what the game genuinely needs (often neither).
//  Sign in with Apple requires the "Sign in with Apple" capability
//  (com.apple.developer.applesignin). StoreKit needs product IDs configured in App Store Connect
//  and, for local testing, a .storekit configuration file in the scheme.
//

import AuthenticationServices
import Security
import StoreKit

// MARK: - Errors

enum AccountError: Error {
    case unexpectedCredential
    case missingIdentityToken
}

// MARK: - Sign in with Apple

/// Wraps the callback-based ASAuthorizationController flow in async/await.
/// Request only the scopes the feature actually uses; `fullName` and `email` arrive ONCE,
/// on the first authorization only, so capture them immediately when present.
@MainActor
final class AppleSignInCoordinator: NSObject {
    private var continuation: CheckedContinuation<ASAuthorizationAppleIDCredential, Error>?

    func signIn(
        scopes: [ASAuthorization.Scope] = [.fullName]  // add .email ONLY if your backend sends mail
    ) async throws -> ASAuthorizationAppleIDCredential {
        let request = ASAuthorizationAppleIDProvider().createRequest()
        request.requestedScopes = scopes

        return try await withCheckedThrowingContinuation { continuation in
            self.continuation = continuation
            let controller = ASAuthorizationController(authorizationRequests: [request])
            controller.delegate = self
            controller.presentationContextProvider = self
            controller.performRequests()
        }
    }

    private func resume(returning credential: ASAuthorizationAppleIDCredential) {
        continuation?.resume(returning: credential)
        continuation = nil
    }

    private func resume(throwing error: Error) {
        continuation?.resume(throwing: error)
        continuation = nil
    }
}

extension AppleSignInCoordinator: ASAuthorizationControllerDelegate {
    func authorizationController(
        controller: ASAuthorizationController,
        didCompleteWithAuthorization authorization: ASAuthorization
    ) {
        guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential else {
            resume(throwing: AccountError.unexpectedCredential)
            return
        }
        resume(returning: credential)
    }

    func authorizationController(
        controller: ASAuthorizationController,
        didCompleteWithError error: Error
    ) {
        // ASAuthorizationError.canceled is a normal user cancel — callers should not show failure UI.
        resume(throwing: error)
    }
}

extension AppleSignInCoordinator: ASAuthorizationControllerPresentationContextProviding {
    func presentationAnchor(for controller: ASAuthorizationController) -> ASPresentationAnchor {
        // Return the active window/scene's anchor in a real app.
        ASPresentationAnchor()
    }
}

// MARK: - Account session (Keychain-backed)

/// The stable `credential.user` identifier is the durable key — store it in the Keychain, never
/// in UserDefaults, and never log tokens. Verify `identityToken` server-side before trusting a sign-in.
@MainActor
final class AccountSession {
    private let coordinator = AppleSignInCoordinator()
    private let userIDKey = "apple_user_id"

    private(set) var userID: String?
    private var revocationObserver: NSObjectProtocol?

    init() {
        userID = Keychain.readString(account: userIDKey)
        observeRevocation()
    }

    deinit {
        if let revocationObserver {
            NotificationCenter.default.removeObserver(revocationObserver)
        }
    }

    /// Optional account creation/sign-in. Never gate core play on this.
    func signIn() async throws {
        let credential = try await coordinator.signIn()

        // Capture the one-time fields NOW; they are nil on every later sign-in.
        let firstAuthName = credential.fullName  // PersonNameComponents?
        let firstAuthEmail = credential.email  // String? — may be an @privaterelay.appleid.com address
        _ = (firstAuthName, firstAuthEmail)  // persist these where your feature needs them

        guard credential.identityToken != nil else {
            throw AccountError.missingIdentityToken
        }
        // Send identityToken + authorizationCode to YOUR server to verify before trusting the sign-in.

        Keychain.writeString(credential.user, account: userIDKey)
        userID = credential.user
    }

    /// Re-check on launch to catch revocations that happened while the app was closed.
    func refreshCredentialState() async {
        guard let savedID = userID else { return }
        let provider = ASAuthorizationAppleIDProvider()
        let state = try? await provider.credentialState(forUserID: savedID)
        switch state {
        case .authorized:
            break
        case .revoked, .notFound, .none:
            signOutLocally()
        case .transferred:
            break  // app moved between developer teams — handle per your backend
        @unknown default:
            break
        }
    }

    func signOutLocally() {
        Keychain.delete(account: userIDKey)
        userID = nil
    }

    private func observeRevocation() {
        revocationObserver = NotificationCenter.default.addObserver(
            forName: ASAuthorizationAppleIDProvider.credentialRevokedNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            // Apple ID was revoked from this app — sign out and clear stored credentials.
            Task { @MainActor in self?.signOutLocally() }
        }
    }
}

// MARK: - Keychain helper (generic password)

enum Keychain {
    static func writeString(_ value: String, account: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: account,
            kSecValueData as String: Data(value.utf8),
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        ]
        SecItemDelete(query as CFDictionary)  // replace any existing value
        SecItemAdd(query as CFDictionary, nil)
    }

    static func readString(account: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
            let data = item as? Data
        else {
            return nil
        }
        return String(decoding: data, as: UTF8.self)
    }

    static func delete(account: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: account,
        ]
        SecItemDelete(query as CFDictionary)
    }
}

// MARK: - StoreKit 2 in-app purchases

/// Digital content/features MUST use StoreKit IAP, never Apple Pay. Grant entitlements only on a
/// `.verified` result; treat `.unverified` as "did not happen." Keep a `Transaction.updates`
/// listener running from launch to catch Ask to Buy approvals, Family Sharing, renewals, and refunds.
@MainActor
final class Store: ObservableObject {
    @Published private(set) var products: [Product] = []
    @Published private(set) var purchasedIDs: Set<String> = []

    private var updatesTask: Task<Void, Never>?

    init() {
        updatesTask = Task { [weak self] in
            for await update in Transaction.updates {
                await self?.handle(verification: update)
            }
        }
    }

    deinit {
        updatesTask?.cancel()
    }

    func loadProducts(ids: [String]) async {
        products = (try? await Product.products(for: ids)) ?? []
    }

    func purchase(_ product: Product) async throws {
        let result = try await product.purchase()
        switch result {
        case .success(let verification):
            await handle(verification: verification)
        case .userCancelled:
            break  // user backed out — do nothing, no nagging
        case .pending:
            break  // Ask to Buy: awaiting parent/Family approval; completes later via Transaction.updates
        @unknown default:
            break
        }
    }

    /// Required for non-consumables: surface a "Restore Purchases" action that calls this.
    func restore() async throws {
        try await AppStore.sync()
        await refreshEntitlements()
    }

    /// Source of truth for "what does this user own right now" — survives reinstalls.
    func refreshEntitlements() async {
        var owned: Set<String> = []
        for await result in Transaction.currentEntitlements {
            guard case .verified(let transaction) = result else { continue }
            if transaction.revocationDate == nil {
                owned.insert(transaction.productID)
            }
        }
        purchasedIDs = owned
    }

    private func handle(verification: VerificationResult<Transaction>) async {
        guard case .verified(let transaction) = verification else { return }  // .unverified ⇒ ignore
        purchasedIDs.insert(transaction.productID)
        await transaction.finish()  // tell StoreKit the content was delivered
    }
}
