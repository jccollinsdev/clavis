import SwiftUI

struct AlertsView: View {
    @Binding var selectedTab: Int
    @StateObject private var viewModel = AlertsViewModel()
    @State private var selectedFilter: AlertsFilter = .all
    @State private var hasLoaded = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if let banner = viewModel.quietHoursBannerText {
                        ClavixCard(fill: .clavixWarnSoft) {
                            Text(banner)
                                .font(ClavisTypography.clavixCaption)
                                .foregroundColor(.clavixWarnInk)
                        }
                    }

                    filterChips

                    if let errorMessage = viewModel.errorMessage, viewModel.alerts.isEmpty {
                        ClavixCard {
                            Text(errorMessage)
                                .font(ClavisTypography.clavixCaption)
                                .foregroundColor(.clavixInk2)
                        }
                    } else if viewModel.isLoading && viewModel.alerts.isEmpty {
                        ClavixCard {
                            Text("Loading alerts…")
                                .font(ClavisTypography.clavixCaption)
                                .foregroundColor(.clavixInk3)
                        }
                    } else if filteredAlerts.isEmpty {
                        ClavixCard {
                            Text("All quiet.")
                                .font(ClavisTypography.clavixCaption)
                                .foregroundColor(.clavixInk3)
                        }
                    } else {
                        ForEach(dayGroupedAlerts, id: \.day) { group in
                            VStack(alignment: .leading, spacing: 8) {
                                Text(group.day)
                                    .font(ClavisTypography.clavixMono(10, weight: .bold))
                                    .tracking(0.7)
                                    .foregroundColor(.clavixInk3)
                                ClavixCard(padding: 0) {
                                    VStack(spacing: 0) {
                                        ForEach(Array(group.alerts.enumerated()), id: \.element.id) { index, alert in
                                            Button(action: { handleAlertTap(alert) }) {
                                                alertRow(alert)
                                            }
                                            .buttonStyle(.plain)
                                            if index < group.alerts.count - 1 {
                                                Rectangle().fill(Color.clavixRule).frame(height: 1)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                .padding(.horizontal, ClavixLayout.pad)
                .padding(.top, 8)
                .padding(.bottom, ClavixLayout.bottomPad)
            }
            .background(Color.clavixPage.ignoresSafeArea())
            .safeAreaInset(edge: .top, spacing: 0) {
                ClavixLargeHeader(
                    eyebrow: alertsEyebrow,
                    title: "Alerts"
                )
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
            .onDisappear {
                viewModel.markAlertsSeen()
            }
        }
    }

    private var alertsEyebrow: String {
        let unread = viewModel.unreadCount
        let total = viewModel.alerts.count
        if total == 0 { return "Alert center" }
        if unread > 0 { return "\(unread) unread · \(total) total" }
        return "\(total) total"
    }

    private var filterChips: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(AlertsFilter.allCases, id: \.title) { filter in
                    Button(action: { selectedFilter = filter }) {
                        Text("\(filter.title) \(filter.apply(to: viewModel.alerts).count)")
                            .font(ClavisTypography.clavixMono(10, weight: .bold))
                            .tracking(0.4)
                            .foregroundColor(selectedFilter == filter ? .clavixPaper : .clavixInk2)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(selectedFilter == filter ? Color.clavixInk : Color.clavixPaper)
                            .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.clavixRule, lineWidth: 1))
                            .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var filteredAlerts: [Alert] {
        selectedFilter.apply(to: viewModel.alerts)
    }

    private struct DayGroup {
        let day: String
        let alerts: [Alert]
    }

    private var dayGroupedAlerts: [DayGroup] {
        let formatter = DateFormatter()
        formatter.dateFormat = "EEE MMM d"
        let calendar = Calendar.current

        var groups: [(key: String, value: [Alert])] = []
        var lookup: [String: Int] = [:]

        for alert in filteredAlerts {
            let label: String
            if calendar.isDateInToday(alert.createdAt) { label = "TODAY" }
            else if calendar.isDateInYesterday(alert.createdAt) { label = "YESTERDAY" }
            else { label = formatter.string(from: alert.createdAt).uppercased() }

            if let idx = lookup[label] {
                groups[idx].value.append(alert)
            } else {
                lookup[label] = groups.count
                groups.append((key: label, value: [alert]))
            }
        }
        return groups.map { DayGroup(day: $0.key, alerts: $0.value) }
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
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Text(label(for: alert).uppercased())
                    .font(ClavisTypography.clavixMono(9, weight: .bold))
                    .tracking(0.4)
                    .foregroundColor(labelColor(for: alert))
                if let ticker = alert.positionTicker, !ticker.isEmpty {
                    Text(ticker)
                        .font(ClavisTypography.clavixMono(11, weight: .bold))
                        .foregroundColor(.clavixAccent)
                }
                Spacer()
                Text(alert.createdAt.formatted(date: .omitted, time: .shortened))
                    .font(ClavisTypography.clavixMono(10, weight: .regular))
                    .foregroundColor(.clavixInk3)
            }

            Text(alert.message.sanitizedDisplayText)
                .font(ClavisTypography.clavixSerif(14, weight: .medium))
                .foregroundColor(.clavixInk)
                .multilineTextAlignment(.leading)
                .lineLimit(3)

            if let previous = alert.previousGrade, let new = alert.newGrade {
                HStack(spacing: 8) {
                    ClavixGradeBadge(previous, size: 22)
                    Image(systemName: "arrow.right")
                        .font(.system(size: 10))
                        .foregroundColor(.clavixInk3)
                    ClavixGradeBadge(new, size: 22)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
    }

    private func label(for alert: Alert) -> String {
        switch alert.type {
        case .gradeChange: return "Grade"
        case .majorEvent: return "News"
        case .portfolioGradeChange, .portfolioSafetyThresholdBreach: return "Portfolio"
        case .digestReady, .ratingReady: return "Update"
        case .macroShock: return "Macro"
        case .safetyDeterioration, .concentrationDanger, .clusterRisk, .structuralFragility: return "Risk"
        }
    }

    private func labelColor(for alert: Alert) -> Color {
        switch alert.type {
        case .digestReady, .ratingReady: return .clavixAccent
        case .gradeChange: return .clavixBad
        case .majorEvent: return .clavixWarn
        case .portfolioGradeChange, .portfolioSafetyThresholdBreach: return .clavixInk
        case .macroShock: return .clavixWarn
        case .safetyDeterioration, .concentrationDanger, .clusterRisk, .structuralFragility: return .clavixBad
        }
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
        case .gradeChanges: return "Grade"
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
