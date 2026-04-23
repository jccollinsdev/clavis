import Foundation
import Network
import SwiftUI

@MainActor
final class NetworkStatusMonitor: ObservableObject {
    static let shared = NetworkStatusMonitor()

    @Published private(set) var isOffline = false

    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "clavis.network.monitor")

    private init() {
        monitor.pathUpdateHandler = { [weak self] path in
            Task { @MainActor in
                self?.isOffline = path.status != .satisfied
            }
        }
        monitor.start(queue: queue)
    }
}

struct OfflineStatusBanner: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Offline")
                .font(.system(size: 15, weight: .semibold))
                .foregroundColor(.red)
            Text("Showing cached data. Actions will retry when the network returns.")
                .font(.system(size: 15))
                .foregroundColor(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(12)
        .background(Color(white: 0.14))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(Color(white: 0.28), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}
