import SwiftUI

struct AlertsView: View {
    @Binding var selectedTab: Int
    @StateObject private var viewModel = AlertsViewModel()
    @State private var selectedFilter: AlertsFilter = .all
    @State private var hasLoaded = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    if let banner = viewModel.quietHoursBannerText {
                        quietHoursBanner(banner)
                    }

                    if let errorMessage = viewModel.errorMessage, viewModel.alerts.isEmpty {
                        DashboardErrorCard(message: errorMessage)
                    } else if viewModel.isLoading && viewModel.alerts.isEmpty {
                        ClavisLoadingCard(title: "Loading alerts", subtitle: "Checking recent alert activity.")
                    } else if filteredAlerts.isEmpty {
                        emptyState
                    } else {
                        ClavisStandardCard(fill: .surface) {
                            VStack(spacing: 0) {
                                ForEach(Array(filteredAlerts.enumerated()), id: \.element.id) { index, alert in
                                    Button(action: { handleAlertTap(alert) }) {
                                        alertRow(alert)
                                    }
                                    .buttonStyle(.plain)

                                    if index < filteredAlerts.count - 1 {
                                        Divider().overlay(Color.border)
                                    }
                                }
                            }
                        }
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, ClavisTheme.sectionSpacing)
                .padding(.bottom, ClavisTheme.extraLargeSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .safeAreaInset(edge: .top, spacing: 0) {
                AlertsTopHeader(selectedFilter: $selectedFilter, unreadCount: viewModel.unreadCount)
            }
            .toolbar(.hidden, for: .navigationBar)
            .task {
                guard !hasLoaded else { return }
                hasLoaded = true
                await viewModel.loadAlerts()
            }
            .refreshable {
                await viewModel.loadAlerts()
            }
        }
    }

    private var filteredAlerts: [Alert] {
        selectedFilter.apply(to: viewModel.alerts)
    }

    private func handleAlertTap(_ alert: Alert) {
        switch destination(for: alert) {
        case .digest:
            selectedTab = 0
        case .holdings:
            selectedTab = 1
        case .ticker(let ticker):
            NotificationCenter.default.post(name: .openPositionDetail, object: ticker)
            selectedTab = 1
        }
    }

    private func destination(for alert: Alert) -> AlertDestination {
        if alert.type == .digestReady || alert.type == .ratingReady { return .digest }
        if let ticker = alert.positionTicker, !ticker.isEmpty { return .ticker(ticker) }
        return .holdings
    }

    private func alertRow(_ alert: Alert) -> some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            HStack(alignment: .firstTextBaseline, spacing: ClavisTheme.smallSpacing) {
                Text(label(for: alert))
                    .font(ClavisTypography.label)
                    .foregroundColor(labelColor(for: alert))
                Spacer()
                Text(relativeDate(alert.createdAt))
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
            }

            if alert.type == .digestReady || alert.type == .ratingReady {
                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                    Text(alert.message.sanitizedDisplayText)
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.textPrimary)
                    HStack {
                        destinationBadge(text: "Read briefing")
                        Spacer()
                    }
                }
                .padding(ClavisTheme.cardPadding)
                .background(Color.accentSoft)
                .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
            } else {
                if let ticker = alert.positionTicker {
                    HStack(spacing: ClavisTheme.smallSpacing) {
                        Text(ticker)
                            .font(ClavisTypography.bodyEmphasis)
                            .foregroundColor(.accentBurnt)
                        if let driver = driverText(for: alert) {
                            destinationBadge(text: driver)
                        }
                    }
                }

                if let previous = alert.previousGrade, let new = alert.newGrade {
                    HStack(spacing: ClavisTheme.smallSpacing) {
                        GradeBadge(grade: previous, size: .compact)
                        Image(systemName: "arrow.right")
                            .foregroundColor(.textSecondary)
                        GradeBadge(grade: new, size: .compact)
                        Text(gradeDeltaText(previous: previous, new: new))
                            .font(ClavisTypography.footnoteEmphasis)
                            .foregroundColor(gradeDeltaColor(previous: previous, new: new))
                    }
                }

                Text(alert.message.sanitizedDisplayText)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)

                HStack(spacing: ClavisTheme.smallSpacing) {
                    if alert.type == .majorEvent || alert.type == .macroShock {
                        destinationBadge(text: impactText(for: alert))
                    }
                    Spacer()
                    destinationBadge(text: destinationText(for: alert))
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, ClavisTheme.mediumSpacing)
    }

    private func quietHoursBanner(_ text: String) -> some View {
        ClavisStandardCard(fill: .surfaceElevated) {
            Text(text)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
        }
    }

    private var emptyState: some View {
        ClavisStandardCard(fill: .surface) {
            Text("No alerts yet — you'll be notified when your holdings' grades change")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func label(for alert: Alert) -> String {
        switch alert.type {
        case .gradeChange: return "Grade Change"
        case .majorEvent: return "Major News"
        case .portfolioGradeChange: return "Portfolio Grade"
        case .digestReady, .ratingReady: return "Digest Ready"
        case .macroShock: return "Portfolio"
        default: return alert.type.displayName
        }
    }

    private func labelColor(for alert: Alert) -> Color {
        switch alert.type {
        case .digestReady, .ratingReady: return .accentBurnt
        case .gradeChange: return .bad
        case .majorEvent: return .warn
        default: return .textSecondary
        }
    }

    private func driverText(for alert: Alert) -> String? {
        guard let details = alert.changeDetails else { return nil }
        if let driver = details["driver"]?.sanitizedDisplayText, !driver.isEmpty { return driver }
        if let dimension = details["dimension"]?.sanitizedDisplayText, !dimension.isEmpty { return dimension }
        return nil
    }

    private func impactText(for alert: Alert) -> String {
        if let details = alert.changeDetails,
           let impact = details["impact_tag"]?.sanitizedDisplayText,
           !impact.isEmpty {
            return impact
        }
        return "Impact"
    }

    private func destinationText(for alert: Alert) -> String {
        switch destination(for: alert) {
        case .digest: return "Today"
        case .holdings: return "Holdings"
        case .ticker(let ticker): return ticker
        }
    }

    private func gradeDeltaText(previous: String, new: String) -> String {
        let delta = Grade.ordinalValue(for: new) - Grade.ordinalValue(for: previous)
        if delta == 0 { return "—" }
        return delta > 0 ? "↑ +\(delta)" : "↓ \(abs(delta))"
    }

    private func gradeDeltaColor(previous: String, new: String) -> Color {
        let delta = Grade.ordinalValue(for: new) - Grade.ordinalValue(for: previous)
        if delta == 0 { return .textSecondary }
        return delta > 0 ? .good : .bad
    }

    private func relativeDate(_ date: Date) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .full
        return formatter.localizedString(for: date, relativeTo: Date())
    }

    private func destinationBadge(text: String) -> some View {
        Text(text)
            .font(ClavisTypography.label)
            .foregroundColor(.textSecondary)
            .padding(.horizontal, 6)
            .padding(.vertical, 4)
            .background(Color.surfaceElevated)
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
    }
}

private enum AlertDestination {
    case digest
    case holdings
    case ticker(String)
}

private enum AlertsFilter: CaseIterable {
    case all
    case gradeChanges
    case news
    case portfolio

    var title: String {
        switch self {
        case .all: return "All"
        case .gradeChanges: return "Grade Changes"
        case .news: return "News"
        case .portfolio: return "Portfolio"
        }
    }

    func apply(to alerts: [Alert]) -> [Alert] {
        let filtered: [Alert] = switch self {
        case .all:
            alerts
        case .gradeChanges:
            alerts.filter { $0.type == .gradeChange }
        case .news:
            alerts.filter { $0.type == .majorEvent }
        case .portfolio:
            alerts.filter { $0.type == .portfolioGradeChange || $0.type == .digestReady || $0.type == .ratingReady || $0.type == .macroShock }
        }
        return filtered.sorted { $0.createdAt > $1.createdAt }
    }
}

private struct AlertsTopHeader: View {
    @Binding var selectedFilter: AlertsFilter
    let unreadCount: Int

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            HStack(spacing: ClavisTheme.smallSpacing) {
                Text("Alerts")
                    .font(ClavisTypography.h2)
                    .foregroundColor(.textPrimary)
                Text("\(unreadCount)")
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.accentInk)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.accentBurnt)
                    .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
            }

            HStack(spacing: ClavisTheme.smallSpacing) {
                ForEach(AlertsFilter.allCases, id: \.title) { filter in
                    Button(action: { selectedFilter = filter }) {
                        Text(filter.title)
                            .font(ClavisTypography.footnoteEmphasis)
                            .foregroundColor(selectedFilter == filter ? .accentInk : .textSecondary)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(selectedFilter == filter ? Color.accentBurnt : Color.surfaceElevated)
                            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .padding(.horizontal, ClavisTheme.screenPadding)
        .padding(.top, ClavisTheme.smallSpacing)
        .padding(.bottom, 6)
        .background(
            Color.backgroundPrimary.opacity(0.9)
                .background(.ultraThinMaterial)
                .ignoresSafeArea(edges: .top)
        )
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(Color.border.opacity(0.5))
                .frame(height: 0.5)
        }
    }
}
