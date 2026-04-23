import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @StateObject private var viewModel = SettingsViewModel()
    @StateObject private var brokerageViewModel = BrokerageViewModel()
    @State private var hasLoaded = false
    @State private var showDeleteAccountConfirmation = false

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    CX2NavBar(transparent: true, showBorder: false)
                    CX2LargeTitle("Settings")

                    if NetworkStatusMonitor.shared.isOffline {
                        OfflineStatusBanner()
                    }

                    DigestSettingsGroup(viewModel: viewModel)

                    BrokerageSettingsGroup(viewModel: brokerageViewModel)

                    AlertsSettingsGroup(viewModel: viewModel)

                    NotificationSettingsGroup(viewModel: viewModel)

                    AccountSettingsGroup(
                        email: viewModel.userEmail,
                        planLabel: planLabel,
                        accountMessage: viewModel.accountMessage,
                        isExporting: viewModel.isExportingAccount,
                        isDeleting: viewModel.isDeletingAccount,
                        onExport: { Task { await viewModel.exportAccount() } },
                        onDelete: { showDeleteAccountConfirmation = true }
                    )

                    AboutSection()

                    SettingsDisclaimerCard()

                    SignOutGroup {
                        Task { await authViewModel.signOut() }
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, 0)
                .padding(.bottom, ClavisTheme.largeSpacing)
            }
            .contentMargins(.top, 0, for: .scrollContent)
            .contentMargins(.bottom, 0, for: .scrollContent)
            .background(ClavisAtmosphereBackground())
            .toolbar(.hidden, for: .navigationBar)
            .onAppear {
                guard !hasLoaded else { return }
                hasLoaded = true
                Task {
                    await viewModel.load()
                    await brokerageViewModel.loadStatus()
                }
            }
            .sheet(
                isPresented: Binding(
                    get: { brokerageViewModel.presentedURL != nil },
                    set: { if !$0 { brokerageViewModel.presentedURL = nil } }
                )
            ) {
                if let url = brokerageViewModel.presentedURL {
                    SafariView(url: url)
                }
            }
            .onReceive(NotificationCenter.default.publisher(for: .snapTradeCallbackReceived)) { notification in
                guard let url = notification.object as? URL else { return }
                Task { await brokerageViewModel.handleCallback(url: url) }
            }
            .alert("Delete your account?", isPresented: $showDeleteAccountConfirmation) {
                Button("Delete", role: .destructive) {
                    Task {
                        if await viewModel.deleteAccount() {
                            await authViewModel.signOut()
                        }
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This permanently deletes your data and account.")
            }
        }
    }

    private var planLabel: String? {
        switch authViewModel.subscriptionTier.lowercased() {
        case "pro":
            return "Clavix Pro"
        case "admin":
            return "Admin"
        default:
            return nil
        }
    }
}

struct BrokerageSettingsGroup: View {
    @ObservedObject var viewModel: BrokerageViewModel

    var body: some View {
        SettingsGroupCard(
            title: "Brokerage",
            footnote: "SnapTrade stays read-only here. Clavix only imports holdings and lets you choose between manual and automatic sync behavior."
        ) {
            if let infoMessage = viewModel.infoMessage {
                SettingsMessageRow(message: infoMessage, color: .informational)
            }

            if let errorMessage = viewModel.errorMessage {
                SettingsMessageRow(message: errorMessage, color: .riskF)
            }

            SettingsStaticRow(
                label: "Status",
                value: viewModel.isConnected ? "Connected" : "Not connected"
            )

            if let connection = viewModel.primaryConnection {
                SettingsStaticRow(
                    label: "Institution",
                    value: connection.institutionName ?? "Connected brokerage"
                )
            }

            if viewModel.isConnected {
                SettingsStaticRow(label: "Sync mode", value: viewModel.autoSyncEnabled ? "Automatic" : "Manual")

                if let lastSyncAt = viewModel.status?.lastSyncAt {
                    SettingsStaticRow(
                        label: "Last sync",
                        value: lastSyncAt.formatted(date: .abbreviated, time: .shortened)
                    )
                }

                if let firstAccount = viewModel.status?.accounts.first {
                    SettingsStaticRow(
                        label: "Account",
                        value: [firstAccount.name, firstAccount.numberMasked].compactMap { $0 }.joined(separator: " · ")
                    )
                }

                SettingsActionRow(
                    title: viewModel.autoSyncEnabled ? "Use manual sync" : "Use automatic sync",
                    tint: .informational
                ) {
                    Task { await viewModel.setAutoSyncEnabled(!viewModel.autoSyncEnabled) }
                }

                if viewModel.primaryConnection?.disabled == true {
                    SettingsActionRow(title: "Reconnect brokerage", tint: .informational) {
                        Task { await viewModel.startConnect(reconnectConnectionId: viewModel.primaryConnection?.id) }
                    }
                }

                SettingsActionRow(
                    title: viewModel.isSyncing ? "Syncing holdings..." : "Sync holdings now",
                    tint: .informational,
                    disabled: viewModel.isSyncing
                ) {
                    Task { await viewModel.syncNow(refreshRemote: true) }
                }

                SettingsActionRow(
                    title: viewModel.isDisconnecting ? "Disconnecting..." : "Disconnect brokerage",
                    tint: .riskF,
                    disabled: viewModel.isDisconnecting,
                    last: true
                ) {
                    Task { await viewModel.disconnect() }
                }
            } else {
                SettingsActionRow(
                    title: viewModel.isLoading ? "Loading..." : "Connect brokerage",
                    tint: .informational,
                    disabled: viewModel.isLoading,
                    last: true
                ) {
                    Task { await viewModel.startConnect() }
                }
            }
        }
    }
}

struct DigestSettingsGroup: View {
    @ObservedObject var viewModel: SettingsViewModel

    var body: some View {
        SettingsGroupCard(
            title: "Digest",
            footnote: "Morning digest is generated from overnight data. Changes save automatically."
        ) {
            SettingsValueRow(label: "Digest time") {
                DatePicker("", selection: $viewModel.digestTime, displayedComponents: .hourAndMinute)
                    .labelsHidden()
                    .onChange(of: viewModel.digestTime) { _, _ in
                        Task { await viewModel.saveDigestTime() }
                    }
            }

            SettingsValueRow(label: "Summary length") {
                Picker("Summary Length", selection: $viewModel.summaryLength) {
                    ForEach(SummaryLength.allCases, id: \.self) { length in
                        Text(length.rawValue).tag(length)
                    }
                }
                .pickerStyle(.segmented)
                .frame(maxWidth: 180)
                .onChange(of: viewModel.summaryLength) { _, _ in
                    Task { await viewModel.saveSummaryLength() }
                }
            }

            SettingsToggleListRow(
                label: "Weekday only",
                subtitle: "Skip weekend digest delivery",
                isOn: $viewModel.weekdayOnly,
                onChange: { Task { await viewModel.saveWeekdayOnly() } },
                last: true
            )
        }
    }
}

struct AlertsSettingsGroup: View {
    @ObservedObject var viewModel: SettingsViewModel

    var body: some View {
        SettingsGroupCard(
            title: "Alerts",
            footnote: "Alert rows cover grade changes, major events, portfolio risk shifts, and large price moves."
        ) {
            SettingsToggleListRow(
                label: "Grade changes",
                subtitle: "Any upgrade or downgrade",
                isOn: $viewModel.alertsGradeChanges,
                onChange: { Task { await viewModel.saveAlertSettings() } }
            )

            SettingsToggleListRow(
                label: "Major events",
                subtitle: "Holdings only",
                isOn: $viewModel.alertsMajorEvents,
                onChange: { Task { await viewModel.saveAlertSettings() } }
            )

            SettingsToggleListRow(
                label: "Portfolio risk changes",
                subtitle: "Composite portfolio score moves",
                isOn: $viewModel.alertsPortfolioRisk,
                onChange: { Task { await viewModel.saveAlertSettings() } }
            )

            SettingsToggleListRow(
                label: "Large price moves",
                subtitle: "Significant daily moves in your holdings",
                isOn: $viewModel.alertsLargePriceMoves,
                onChange: { Task { await viewModel.saveAlertSettings() } }
            )

            SettingsToggleListRow(
                label: "Quiet hours",
                subtitle: "Suppress alerts overnight",
                isOn: $viewModel.quietHoursEnabled,
                onChange: { Task { await viewModel.saveAlertSettings() } },
                last: viewModel.quietHoursEnabled == false
            )

            if viewModel.quietHoursEnabled {
                SettingsValueRow(label: "From") {
                    DatePicker("", selection: $viewModel.quietHoursStart, displayedComponents: .hourAndMinute)
                        .labelsHidden()
                        .onChange(of: viewModel.quietHoursStart) { _, _ in
                            Task { await viewModel.saveAlertSettings() }
                        }
                }

                SettingsValueRow(label: "To", last: true) {
                    DatePicker("", selection: $viewModel.quietHoursEnd, displayedComponents: .hourAndMinute)
                        .labelsHidden()
                        .onChange(of: viewModel.quietHoursEnd) { _, _ in
                            Task { await viewModel.saveAlertSettings() }
                        }
                }
            }
        }
    }
}

struct NotificationSettingsGroup: View {
    @ObservedObject var viewModel: SettingsViewModel

    var body: some View {
        SettingsGroupCard(title: "Notifications") {
            SettingsToggleListRow(
                label: "Push notifications",
                subtitle: "Controls whether the app sends digest and alert pushes",
                isOn: $viewModel.notificationsEnabled,
                onChange: { Task { await viewModel.saveNotifications() } },
                last: true
            )
        }
    }
}

struct AccountSettingsGroup: View {
    let email: String
    let planLabel: String?
    let accountMessage: String?
    let isExporting: Bool
    let isDeleting: Bool
    let onExport: () -> Void
    let onDelete: () -> Void

    var body: some View {
        SettingsGroupCard(title: "Account") {
            SettingsStaticRow(label: "Profile", value: email)

            if let planLabel {
                SettingsStaticRow(label: "Plan", value: planLabel)
            }

            if let accountMessage {
                SettingsMessageRow(message: accountMessage, color: .informational)
            }

            SettingsActionRow(
                title: isExporting ? "Exporting..." : "Export my data",
                tint: .informational,
                disabled: isExporting
            ) {
                onExport()
            }

            SettingsActionRow(
                title: isDeleting ? "Deleting..." : "Delete account",
                tint: .riskF,
                disabled: isDeleting,
                last: true
            ) {
                onDelete()
            }
        }
    }
}

struct SettingsGroupCard<Content: View>: View {
    let title: String?
    let footnote: String?
    @ViewBuilder let content: Content

    init(title: String? = nil, footnote: String? = nil, @ViewBuilder content: () -> Content) {
        self.title = title
        self.footnote = footnote
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let title, !title.isEmpty {
                CX2SectionLabel(text: title)
                    .foregroundColor(.textSecondary)
                    .padding(.leading, 2)
            }

            VStack(spacing: 0) {
                content
            }
            .padding(.horizontal, 14)
            .clavisCardStyle(fill: .surface)

            if let footnote, !footnote.isEmpty {
                Text(footnote)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                    .padding(.leading, 2)
            }
        }
    }
}

struct SettingsToggleListRow: View {
    let label: String
    let subtitle: String?
    @Binding var isOn: Bool
    let onChange: () -> Void
    var last: Bool = false

    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(label)
                    .font(.system(size: 15, weight: .regular))
                    .foregroundColor(.textPrimary)

                if let subtitle, !subtitle.isEmpty {
                    Text(subtitle)
                        .font(.system(size: 12, weight: .regular))
                        .foregroundColor(.textSecondary)
                }
            }

            Spacer()

            Button {
                isOn.toggle()
                onChange()
            } label: {
                CX2Toggle(isOn: $isOn)
            }
            .buttonStyle(.plain)
        }
        .padding(.vertical, 13)
        .overlay(alignment: .bottom) {
            if !last {
                Rectangle()
                    .fill(Color.border)
                    .frame(height: 1)
            }
        }
    }
}

struct SettingsValueRow<ValueView: View>: View {
    let label: String
    var last: Bool = false
    @ViewBuilder let valueView: ValueView

    init(label: String, last: Bool = false, @ViewBuilder valueView: () -> ValueView) {
        self.label = label
        self.last = last
        self.valueView = valueView()
    }

    var body: some View {
        HStack(spacing: 12) {
            Text(label)
                .font(.system(size: 15, weight: .regular))
                .foregroundColor(.textPrimary)

            Spacer()

            valueView
        }
        .padding(.vertical, 13)
        .overlay(alignment: .bottom) {
            if !last {
                Rectangle()
                    .fill(Color.border)
                    .frame(height: 1)
            }
        }
    }
}

struct SettingsStaticRow: View {
    let label: String
    let value: String
    var last: Bool = false

    var body: some View {
        HStack(spacing: 12) {
            Text(label)
                .font(.system(size: 15, weight: .regular))
                .foregroundColor(.textPrimary)

            Spacer()

            Text(value)
                .font(.system(size: 14, weight: .regular))
                .foregroundColor(.textSecondary)
        }
        .padding(.vertical, 13)
        .overlay(alignment: .bottom) {
            if !last {
                Rectangle()
                    .fill(Color.border)
                    .frame(height: 1)
            }
        }
    }
}

struct SettingsMessageRow: View {
    let message: String
    let color: Color
    var last: Bool = false

    var body: some View {
        Text(message)
            .font(ClavisTypography.footnote)
            .foregroundColor(color)
            .padding(.vertical, 13)
            .frame(maxWidth: .infinity, alignment: .leading)
            .overlay(alignment: .bottom) {
                if !last {
                    Rectangle()
                        .fill(Color.border)
                        .frame(height: 1)
                }
            }
    }
}

struct SettingsActionRow: View {
    let title: String
    let tint: Color
    var disabled: Bool = false
    var last: Bool = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Text(title)
                    .font(.system(size: 15, weight: .regular))
                    .foregroundColor(disabled ? .textTertiary : tint)
                Spacer()
                CX2Chevron()
            }
            .padding(.vertical, 13)
        }
        .buttonStyle(.plain)
        .disabled(disabled)
        .overlay(alignment: .bottom) {
            if !last {
                Rectangle()
                    .fill(Color.border)
                    .frame(height: 1)
            }
        }
    }
}

struct AboutSection: View {
    var body: some View {
        SettingsGroupCard(title: "About") {
            SettingsStaticRow(label: "Clavix", value: "v1.0.0")

            NavigationLink(destination: ScoreExplanationView()) {
                SettingsNavigationRow(title: "Score explanation")
            }
            .buttonStyle(.plain)

            NavigationLink(destination: MethodologyView()) {
                SettingsNavigationRow(title: "Data sources & methodology")
            }
            .buttonStyle(.plain)

            SettingsLinkRow(title: "Methodology", urlString: "https://getclavix.com/methodology")
            SettingsLinkRow(title: "Privacy policy", urlString: "https://getclavix.com/privacy")
            SettingsLinkRow(title: "Terms of service", urlString: "https://getclavix.com/terms")
            SettingsLinkRow(title: "Refund policy", urlString: "https://getclavix.com/refund", last: true)
        }
    }
}

struct SettingsNavigationRow: View {
    let title: String
    var last: Bool = false

    var body: some View {
        HStack {
            Text(title)
                .font(ClavisTypography.body)
                .foregroundColor(.textPrimary)
            Spacer()
            Image(systemName: "chevron.right")
                .font(.system(size: 15, weight: .semibold))
                .foregroundColor(.textTertiary)
        }
        .padding(.vertical, 13)
        .overlay(alignment: .bottom) {
            if !last {
                Rectangle()
                    .fill(Color.border)
                    .frame(height: 1)
            }
        }
    }
}

struct SettingsLinkRow: View {
    let title: String
    let urlString: String
    var last: Bool = false

    var body: some View {
        if let url = URL(string: urlString) {
            Link(destination: url) {
                HStack {
                    Text(title)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textPrimary)
                    Spacer()
                    Image(systemName: "arrow.up.right")
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundColor(.textTertiary)
                }
                .padding(.vertical, 13)
                .overlay(alignment: .bottom) {
                    if !last {
                        Rectangle()
                            .fill(Color.border)
                            .frame(height: 1)
                    }
                }
            }
        }
    }
}
struct SettingsDisclaimerCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Informational only")
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)

            Text(ClavisCopy.settingsDisclaimer)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(14)
        .clavisCardStyle(fill: .surfaceElevated)
    }
}

struct SignOutGroup: View {
    let onSignOut: () -> Void

    var body: some View {
        SettingsGroupCard {
            Button(role: .destructive, action: onSignOut) {
                HStack {
                    Text("Sign out")
                        .font(ClavisTypography.body)
                    Spacer()
                }
                .padding(.vertical, 13)
            }
            .buttonStyle(.plain)
        }
    }
}

struct ScoreExplanationView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.largeSpacing) {
                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                    Text("How Risk Scores Work")
                        .font(ClavisTypography.sectionTitle)
                        .foregroundColor(.textPrimary)

                    Text("Scores range from 0 to 100, where 100 represents minimum risk and 0 represents extreme risk.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }

                VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                    ScoreBandRow(grade: "A", range: "80–100", description: "Safe — minimum risk exposure", color: .riskA)
                    ScoreBandRow(grade: "B", range: "65–79", description: "Stable — low risk", color: .riskB)
                    ScoreBandRow(grade: "C", range: "50–64", description: "Watch — moderate risk", color: .riskC)
                    ScoreBandRow(grade: "D", range: "35–49", description: "Risky — elevated risk", color: .riskD)
                    ScoreBandRow(grade: "F", range: "0–34", description: "Critical — high risk", color: .riskF)
                }

                Text("Informational only. Scores reflect model output based on available data. They do not constitute financial advice.")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }
            .padding(ClavisTheme.cardPadding)
        }
        .background(ClavisAtmosphereBackground())
        .navigationTitle("Score Explanation")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct ScoreBandRow: View {
    let grade: String
    let range: String
    let description: String
    let color: Color

    var body: some View {
        HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
            GradeTag(grade: grade)

            VStack(alignment: .leading, spacing: 2) {
                Text(range)
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(color)
                Text(description)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
            }
            Spacer()
        }
        .padding(ClavisTheme.cardPadding)
        .clavisSecondaryCardStyle(fill: .surfaceElevated)
    }
}

struct MethodologyView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.largeSpacing) {
                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                    Text("Methodology Overview")
                        .font(ClavisTypography.sectionTitle)
                        .foregroundColor(.textPrimary)

                    Text("Clavix evaluates positions across multiple risk dimensions including market structure, macro sensitivity, sentiment, and catalyst quality.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }

                VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                    MethodologyStepRow(number: "01", title: "Data Collection", description: "Real-time price, news, and market structure signals are gathered for each position.")
                    MethodologyStepRow(number: "02", title: "Relevance Filtering", description: "Market noise is filtered out so only position-relevant stories move forward.")
                    MethodologyStepRow(number: "03", title: "Risk Analysis", description: "Each position is scored across four dimensions: news sentiment, macro exposure, position sizing, and volatility trend.")
                    MethodologyStepRow(number: "04", title: "Grade Assignment", description: "Composite scores are mapped to letter grades with fixed boundaries.")
                }

                Text("All scores are informational model outputs only. They do not constitute financial advice and should not be used as the sole basis for investment decisions.")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textTertiary)
            }
            .padding(ClavisTheme.cardPadding)
        }
        .background(ClavisAtmosphereBackground())
        .navigationTitle("Methodology")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct MethodologyStepRow: View {
    let number: String
    let title: String
    let description: String

    var body: some View {
        HStack(alignment: .top, spacing: ClavisTheme.mediumSpacing) {
            Text(number)
                .font(ClavisTypography.label)
                .foregroundColor(.textTertiary)
                .frame(width: 24, alignment: .leading)

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(.textPrimary)
                Text(description)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisSecondaryCardStyle(fill: .surfaceElevated)
    }
}
