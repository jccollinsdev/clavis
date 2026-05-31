import SwiftUI

struct AlertsView: View {
    @Binding var selectedTab: Int
    @StateObject private var viewModel = AlertsViewModel()
    @State private var selectedFilter: AlertsFilter = .all
    @State private var hasLoaded = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    if let banner = viewModel.quietHoursBannerText {
                        ClavixCard(fill: .clavixWarnSoft) {
                            Text(banner)
                                .font(ClavisTypography.clavixCaption)
                                .foregroundColor(.clavixWarnInk)
                        }
                        .padding(.horizontal, ClavixLayout.pad)
                    }

                    filterChips
                        .padding(.horizontal, ClavixLayout.pad)

                    alertsSummaryCard
                        .padding(.horizontal, ClavixLayout.pad)

                    if let errorMessage = viewModel.errorMessage, viewModel.alerts.isEmpty {
                        ClavixInlineNoticeCard(
                            eyebrow: "Alerts",
                            title: "Alerts are temporarily unavailable",
                            message: errorMessage,
                            footnote: "Morning Reports still act as the primary daily briefing when alert loading fails.",
                            glyph: "wifi.exclamationmark",
                            fill: .clavixBadSoft,
                            foreground: .clavixBadInk,
                            secondary: .clavixBadInk
                        )
                        .padding(.horizontal, ClavixLayout.pad)
                    } else if viewModel.isLoading && viewModel.alerts.isEmpty {
                        ClavixInlineNoticeCard(
                            eyebrow: "Alerts",
                            title: "Loading your alert tape",
                            message: "Clavix is pulling recent grade changes, risk notices, and major news tied to your portfolio.",
                            glyph: "bell.badge"
                        )
                        .padding(.horizontal, ClavixLayout.pad)
                    } else if filteredAlerts.isEmpty {
                        emptyState
                    } else {
                        ForEach(dayGroupedAlerts, id: \.day) { group in
                            VStack(alignment: .leading, spacing: 0) {
                                daySeparator(group.day)
                                    .padding(.horizontal, ClavixLayout.pad)
                                ForEach(group.alerts, id: \.id) { alert in
                                    Button(action: { handleAlertTap(alert) }) {
                                        alertRow(alert)
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                        }
                    }
                }
                .padding(.top, 8)
                .padding(.bottom, ClavixLayout.bottomPad)
            }
            .background(Color.clavixPage.ignoresSafeArea())
            .safeAreaInset(edge: .top, spacing: 0) {
                ClavixStickyBar(trailing: AnyView(
                    HStack(spacing: 18) {
                        Image(systemName: "slider.horizontal.3")
                            .foregroundColor(.clavixInk)
                        Button(action: { Task { try? await APIService.shared.markAllAlertsRead(); viewModel.markAlertsSeen() } }) {
                            Image(systemName: "checkmark")
                                .foregroundColor(.clavixInk)
                        }
                        .buttonStyle(.plain)
                    }
                ))
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

    private var alertsSummaryCard: some View {
        ClavixInlineNoticeCard(
            eyebrow: alertsEyebrow,
            title: alertsSummaryTitle,
            message: alertsSummaryMessage,
            footnote: selectedFilter == .all ? "The Morning Report remains the authoritative daily summary." : "Filter counts reflect the last 7 days of captured activity.",
            glyph: "bell.badge"
        )
    }

    private var alertsEyebrow: String {
        let unread = viewModel.unreadCount
        let total = viewModel.alerts.count
        if total == 0 { return "Alert center" }
        return "\(unread) unread · \(total) in 7D"
    }

    private var alertsSummaryTitle: String {
        if viewModel.isLoading && viewModel.alerts.isEmpty {
            return "Reviewing the latest portfolio signals"
        }
        if viewModel.alerts.isEmpty {
            return "No captured alerts yet"
        }
        let filteredCount = filteredAlerts.count
        if selectedFilter == .all {
            return "\(filteredCount) alert\(filteredCount == 1 ? "" : "s") ready for review"
        }
        return "\(selectedFilter.title) alerts narrowed to \(filteredCount)"
    }

    private var alertsSummaryMessage: String {
        if viewModel.isLoading && viewModel.alerts.isEmpty {
            return "Alerts surface notable changes between Morning Reports, but they only appear when data has actually been captured."
        }
        if viewModel.alerts.isEmpty {
            return "Grade changes, portfolio risk notices, and major news will appear here once Clavix has something worth flagging."
        }
        return "Use alerts for triage, then open a ticker or return to Today when you need the full narrative behind a move."
    }

    private var filterChips: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 4) {
                ForEach(AlertsFilter.allCases, id: \.title) { filter in
                    let count = filter.apply(to: viewModel.alerts).count
                    Button(action: { selectedFilter = filter }) {
                        ClavixPill(label: "\(filter.title) · \(count)", active: selectedFilter == filter)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var emptyState: some View {
        ClavixInlineNoticeCard(
            eyebrow: "All quiet",
            title: "No alerts match this filter",
            message: "Clavix has not captured any \(selectedFilter.title.lowercased()) alerts in the current view.",
            footnote: "Morning Reports still arrive on schedule even when the alert tape is quiet.",
            glyph: "bell.slash"
        )
        .padding(.horizontal, ClavixLayout.pad)
    }

    private func daySeparator(_ label: String) -> some View {
        HStack(spacing: 10) {
            Text(label.uppercased())
                .font(ClavisTypography.clavixMono(10, weight: .semibold))
                .tracking(0.7)
                .foregroundColor(.clavixInk3)
            Rectangle().fill(Color.clavixRule).frame(height: 1)
        }
        .padding(.top, 8)
        .padding(.bottom, 4)
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
            if calendar.isDateInToday(alert.createdAt) {
                label = "Today · \(formatter.string(from: alert.createdAt))"
            } else if calendar.isDateInYesterday(alert.createdAt) {
                label = "Yesterday · \(formatter.string(from: alert.createdAt))"
            } else {
                label = formatter.string(from: alert.createdAt)
            }

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
        // Mark read on the server (idempotent; ignores failure).
        Task { try? await APIService.shared.markAlertRead(id: alert.id) }
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

    /// VQAAlertCenterRow 1:1 — category pill + time on left, title + body +
    /// grade/delta in the middle, chevron on right. Tinted background +
    /// accent strip when unread.
    private func alertRow(_ alert: Alert) -> some View {
        let tone = alertTone(alert)
        let isUnread = alert.isUnread(seenAt: viewModel.lastSeenAtPublic)
        return HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(label(for: alert).uppercased())
                    .font(ClavisTypography.clavixMono(9, weight: .bold))
                    .tracking(0.5)
                    .foregroundColor(.white)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(tone)
                    .clipShape(RoundedRectangle(cornerRadius: 3))
                Text(alert.createdAt.formatted(date: .omitted, time: .shortened))
                    .font(ClavisTypography.clavixMono(10, weight: .regular))
                    .foregroundColor(.clavixInk3)
            }
            .frame(width: 56, alignment: .leading)

            VStack(alignment: .leading, spacing: 4) {
                Text(headline(for: alert))
                    .font(ClavisTypography.inter(13, weight: isUnread ? .semibold : .medium))
                    .foregroundColor(.clavixInk)
                    .fixedSize(horizontal: false, vertical: true)
                if let body = bodyText(for: alert) {
                    Text(body)
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                        .fixedSize(horizontal: false, vertical: true)
                }
                if alert.newGrade != nil || alert.changeDetails?["score_delta"] != nil {
                    HStack(spacing: 6) {
                        if let grade = alert.newGrade, !grade.isEmpty {
                            ClavixGradeBadge(grade, size: 18)
                        }
                        if let delta = parseDelta(alert.changeDetails?["score_delta"]) {
                            Text(delta == 0 ? "—" : delta > 0 ? "▲ \(delta)" : "▼ \(abs(delta))")
                                .font(ClavisTypography.clavixMono(10, weight: .semibold))
                                .foregroundColor(delta < 0 ? .clavixBad : .clavixGood)
                        }
                    }
                    .padding(.top, 4)
                }
            }
            Spacer(minLength: 8)
            Image(systemName: "chevron.right")
                .font(.system(size: 10))
                .foregroundColor(.clavixInk4)
                .padding(.top, 2)
        }
        .padding(.horizontal, ClavixLayout.pad)
        .padding(.vertical, 12)
        .background(isUnread ? Color.clavixPaper : Color.clear)
        .overlay(alignment: .leading) {
            if isUnread { Rectangle().fill(Color.clavixAccent).frame(width: 3) }
        }
        .overlay(alignment: .bottom) {
            Rectangle().fill(Color.clavixRule2).frame(height: 1).padding(.leading, ClavixLayout.pad)
        }
    }

    private func headline(for alert: Alert) -> String {
        let text = alert.message.sanitizedDisplayText
        if let dot = text.firstIndex(of: ".") {
            return String(text[..<dot]).trimmingCharacters(in: .whitespaces)
        }
        return text
    }

    private func bodyText(for alert: Alert) -> String? {
        let text = alert.message.sanitizedDisplayText
        guard let dot = text.firstIndex(of: ".") else { return nil }
        let after = text[text.index(after: dot)...].trimmingCharacters(in: .whitespaces)
        return after.isEmpty ? nil : String(after)
    }

    private func parseDelta(_ raw: String?) -> Int? {
        guard let raw, let value = Int(raw.replacingOccurrences(of: "+", with: "")) else { return nil }
        return value
    }

    private func label(for alert: Alert) -> String {
        switch alert.type {
        case .gradeChange:                                             return "GRADE"
        case .majorEvent:                                              return "NEWS"
        case .portfolioGradeChange, .portfolioSafetyThresholdBreach:   return "PORT"
        case .digestReady, .ratingReady:                                return "PORT"
        case .macroShock:                                              return "MACRO"
        case .safetyDeterioration, .concentrationDanger,
             .clusterRisk, .structuralFragility:                       return "RISK"
        }
    }

    private func alertTone(_ alert: Alert) -> Color {
        switch alert.type {
        case .gradeChange, .safetyDeterioration:                       return .clavixBad
        case .majorEvent, .macroShock:                                 return .clavixWarn
        case .portfolioGradeChange, .portfolioSafetyThresholdBreach,
             .digestReady, .ratingReady:                                return .clavixInk
        case .concentrationDanger, .clusterRisk, .structuralFragility: return .clavixBad
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
    case macro

    var title: String {
        switch self {
        case .all: return "All"
        case .gradeChanges: return "Grade"
        case .news: return "News"
        case .portfolio: return "Portfolio"
        case .macro: return "Macro"
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
            alerts.filter { $0.type == .portfolioGradeChange || $0.type == .digestReady || $0.type == .ratingReady || $0.type == .portfolioSafetyThresholdBreach }
        case .macro:
            alerts.filter { $0.type == .macroShock }
        }
        return filtered.sorted { $0.createdAt > $1.createdAt }
    }
}

private extension Alert {
    func isUnread(seenAt: Date?) -> Bool {
        guard let seenAt else { return true }
        return createdAt > seenAt
    }
}
