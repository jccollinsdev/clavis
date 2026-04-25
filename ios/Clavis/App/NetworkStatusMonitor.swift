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
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "wifi.slash")
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(.riskD)
                .padding(.top, 2)

            VStack(alignment: .leading, spacing: 3) {
                Text("Offline")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(.textPrimary)
                Text("Showing cached data. Actions will retry when the network returns.")
                    .font(.system(size: 12, weight: .regular))
                    .foregroundColor(.textSecondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 0)
        }
        .padding(12)
        .background(Color.surface)
        .overlay(
            RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                .stroke(Color.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
    }
}
