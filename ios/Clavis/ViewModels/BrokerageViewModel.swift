import Foundation
import SwiftUI

extension Notification.Name {
    static let snapTradeCallbackReceived = Notification.Name("snapTradeCallbackReceived")
}

@MainActor
final class BrokerageViewModel: ObservableObject {
    @Published var status: APIService.BrokerageStatusResponse?
    @Published var presentedURL: URL?
    @Published var isLoading = false
    @Published var isSyncing = false
    @Published var isDisconnecting = false
    @Published var isSavingSettings = false
    @Published var errorMessage: String?
    @Published var infoMessage: String?

    private let api = APIService.shared

    var isConnected: Bool {
        status?.connected ?? false
    }

    var autoSyncEnabled: Bool {
        status?.autoSyncEnabled ?? false
    }

    var primaryConnection: APIService.BrokerageConnection? {
        status?.connections.first
    }

    func loadStatus() async {
        isLoading = true
        defer { isLoading = false }
        do {
            status = try await retryingUnauthorized {
                try await self.api.fetchBrokerageStatus()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func startConnect(reconnectConnectionId: String? = nil) async {
        errorMessage = nil
        infoMessage = nil
        do {
            let response = try await retryingUnauthorized {
                try await self.api.createBrokerageConnectLink(reconnectConnectionId: reconnectConnectionId)
            }
            guard let url = URL(string: response.redirectURI) else {
                errorMessage = "The brokerage link was invalid."
                return
            }
            presentedURL = url
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func setAutoSyncEnabled(_ enabled: Bool) async {
        isSavingSettings = true
        defer { isSavingSettings = false }
        do {
            try await retryingUnauthorized {
                try await self.api.updateBrokerageSettings(autoSyncEnabled: enabled)
            }
            status = try await retryingUnauthorized {
                try await self.api.fetchBrokerageStatus()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func syncNow(refreshRemote: Bool = true) async {
        isSyncing = true
        errorMessage = nil
        defer { isSyncing = false }
        do {
            let response = try await retryingUnauthorized {
                try await self.api.syncBrokerage(refreshRemote: refreshRemote)
            }
            status = try await retryingUnauthorized {
                try await self.api.fetchBrokerageStatus()
            }
            let imported = response.createdPositions + response.updatedPositions
            infoMessage = imported > 0
                ? "Brokerage sync complete. Imported or refreshed \(imported) holding\(imported == 1 ? "" : "s")."
                : "Brokerage sync complete. No holdings needed to change."
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func disconnect() async {
        isDisconnecting = true
        errorMessage = nil
        defer { isDisconnecting = false }
        do {
            try await retryingUnauthorized {
                try await self.api.disconnectBrokerage()
            }
            status = try await retryingUnauthorized {
                try await self.api.fetchBrokerageStatus()
            }
            infoMessage = "Brokerage disconnected. Synced holdings were removed from Clavix."
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func handleCallback(url: URL) async {
        presentedURL = nil

        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: true) else {
            errorMessage = "The brokerage callback could not be read."
            return
        }
        let params = Dictionary(uniqueKeysWithValues: (components.queryItems ?? []).map { ($0.name, $0.value ?? "") })
        let statusValue = (params["status"] ?? "").uppercased()

        switch statusValue {
        case "SUCCESS":
            infoMessage = "Brokerage connected. Importing holdings..."
            await syncNow(refreshRemote: false)
        case "ERROR":
            let errorCode = params["error_code"] ?? "Unknown error"
            errorMessage = "Brokerage connection failed: \(errorCode)"
        case "ABANDONED":
            infoMessage = "Brokerage connection was cancelled before completion."
        default:
            break
        }
    }

    private func retryingUnauthorized<T>(_ operation: @escaping () async throws -> T) async throws -> T {
        do {
            return try await operation()
        } catch let error as APIError {
            guard case .unauthorized = error else { throw error }
            try? await Task.sleep(nanoseconds: 750_000_000)
            return try await operation()
        }
    }
}
