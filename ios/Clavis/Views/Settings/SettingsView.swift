import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @StateObject private var viewModel = SettingsViewModel()
    @StateObject private var brokerageViewModel = BrokerageViewModel()
    @State private var hasLoaded = false
    @State private var showDeleteAccountConfirmation = false
    @State private var showUpgradeSheet = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    accountHeader
                    digestSection
                    alertsSection
                    quietHoursSection
                    brokerageSection
                    dataSection
                    legalSection
                    methodologyLinks
                    versionFooter
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, ClavisTheme.sectionSpacing)
                .padding(.bottom, ClavisTheme.extraLargeSpacing)
            }
            .background(Color.clavixPage.ignoresSafeArea())
            .safeAreaInset(edge: .top, spacing: 0) {
                ClavixLargeHeader(eyebrow: "Account", title: "Settings")
            }
            .toolbar(.hidden, for: .navigationBar)
            .task {
                guard !hasLoaded else { return }
                hasLoaded = true
                await viewModel.load()
                await brokerageViewModel.loadStatus()
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
            .sheet(isPresented: $showUpgradeSheet) {
                SettingsUpgradeSheet()
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

    private var topHeader: some View {
        ClavixPageHeader(title: "Settings")
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
                    .fill(Color.clavixRule.opacity(0.5))
                    .frame(height: 0.5)
            }
    }

    private var accountHeader: some View {
        ClavixCard(fill: .clavixPaper) {
            HStack(alignment: .center, spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(viewModel.userName.isEmpty ? viewModel.userEmail : viewModel.userName)
                        .font(ClavisTypography.clavixSerif(24, weight: .medium))
                        .foregroundColor(.clavixInk)
                    Text(viewModel.userEmail)
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(.clavixInk3)
                }
                Spacer()
                tierBadge
            }
        }
    }

    private var digestSection: some View {
        settingsGroup(title: "Digest preferences") {
            settingsRow(title: "Delivery time") {
                DatePicker("Delivery time", selection: $viewModel.digestTime, displayedComponents: .hourAndMinute)
                    .labelsHidden()
                    .tint(.clavixAccent)
                    .onChange(of: viewModel.digestTime) { _ in
                        Task { await viewModel.saveDigestTime() }
                    }
            }

            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text("Length")
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(.clavixInk)
                HStack(spacing: ClavisTheme.smallSpacing) {
                    ForEach(SummaryLength.allCases, id: \.rawValue) { option in
                        Button(action: { selectDigestLength(option) }) {
                            HStack(spacing: 4) {
                                Text(option.rawValue)
                                if option == .verbose {
                                    Text("Pro")
                                        .font(ClavisTypography.label)
                                }
                            }
                            .font(ClavisTypography.footnoteEmphasis)
                            .foregroundColor(viewModel.summaryLength == option ? .clavixAccentInk : .clavixInk3)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 8)
                            .background(viewModel.summaryLength == option ? Color.clavixAccent : Color.clavixPaper2)
                            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.innerCornerRadius, style: .continuous))
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private var alertsSection: some View {
        settingsGroup(title: "Alert preferences") {
            toggleRow(title: "Grade changes", isOn: $viewModel.alertsGradeChanges)
            toggleRow(title: "Major news", isOn: $viewModel.alertsMajorEvents)
            toggleRow(title: "Portfolio grade", isOn: $viewModel.alertsPortfolioRisk)
        }
    }

    private var quietHoursSection: some View {
        settingsGroup(title: "Quiet hours") {
            toggleRow(title: "Quiet hours enabled", isOn: $viewModel.quietHoursEnabled)

            settingsRow(title: "Start") {
                DatePicker("Start", selection: $viewModel.quietHoursStart, displayedComponents: .hourAndMinute)
                    .labelsHidden()
                    .tint(.clavixAccent)
                    .onChange(of: viewModel.quietHoursStart) { _ in
                        Task { await viewModel.saveAlertSettings() }
                    }
            }

            settingsRow(title: "End") {
                DatePicker("End", selection: $viewModel.quietHoursEnd, displayedComponents: .hourAndMinute)
                    .labelsHidden()
                    .tint(.clavixAccent)
                    .onChange(of: viewModel.quietHoursEnd) { _ in
                        Task { await viewModel.saveAlertSettings() }
                    }
            }
        }
    }

    private var brokerageSection: some View {
        settingsGroup(title: "Brokerage") {
            settingsStaticRow(title: "Status", value: brokerageViewModel.isConnected ? "Connected" : "Not connected")
            settingsStaticRow(title: "Sync status", value: brokerageViewModel.autoSyncEnabled ? "Automatic" : "Manual")
            settingsStaticRow(title: "Last synced", value: brokerageViewModel.status?.lastSyncAt?.formatted(date: .abbreviated, time: .shortened) ?? "Never")

            if brokerageViewModel.isConnected {
                settingsActionRow(title: brokerageViewModel.isSyncing ? "Syncing holdings..." : "Sync holdings now") {
                    Task { await brokerageViewModel.syncNow(refreshRemote: true) }
                }
                settingsActionRow(title: brokerageViewModel.isDisconnecting ? "Disconnecting..." : "Disconnect brokerage", destructive: true) {
                    Task { await brokerageViewModel.disconnect() }
                }
            } else {
                settingsActionRow(title: "Connect brokerage") {
                    Task { await brokerageViewModel.startConnect() }
                }
            }
        }
    }

    private var dataSection: some View {
        settingsGroup(title: "Data") {
            settingsActionRow(title: viewModel.isExportingAccount ? "Exporting..." : "Export account data") {
                Task { await viewModel.exportAccount() }
            }
            settingsActionRow(title: viewModel.isDeletingAccount ? "Deleting..." : "Delete account", destructive: true) {
                showDeleteAccountConfirmation = true
            }
        }
    }

    private var legalSection: some View {
        settingsGroup(title: "Legal") {
            linkRow(title: "Privacy Policy", urlString: "https://getclavix.com/privacy")
            linkRow(title: "Terms of Service", urlString: "https://getclavix.com/terms")
        }
    }

    private var methodologyLinks: some View {
        settingsGroup(title: "Methodology") {
            NavigationLink(destination: MethodologyView()) {
                settingsChevronRow(title: "Data sources & methodology")
            }
            .buttonStyle(.plain)
            NavigationLink(destination: ScoreExplanationView()) {
                settingsChevronRow(title: "Score explanation")
            }
            .buttonStyle(.plain)
        }
    }

    private var versionFooter: some View {
        VStack(alignment: .center, spacing: ClavisTheme.smallSpacing) {
            Text(ClavisCopy.appVersionString)
                .font(ClavisTypography.footnote)
                .foregroundColor(.clavixInk3)
            Button("Sign out") {
                Task { await authViewModel.signOut() }
            }
            .font(ClavisTypography.footnoteEmphasis)
            .foregroundColor(.clavixInk3)
            .buttonStyle(.plain)
        }
        .frame(maxWidth: .infinity)
    }

    private var tierBadge: some View {
        Text(isFreeTier ? "FREE" : viewModel.subscriptionTier.uppercased())
            .font(ClavisTypography.clavixMono(10, weight: .bold))
            .tracking(0.4)
            .foregroundColor(isFreeTier ? .clavixInk3 : .clavixAccentInk)
            .padding(.horizontal, 8)
            .padding(.vertical, 6)
            .background(isFreeTier ? Color.clavixPaper2 : Color.clavixAccentSoft)
            .overlay(RoundedRectangle(cornerRadius: 4).stroke(isFreeTier ? Color.clavixRule : Color.clavixAccent.opacity(0.3), lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))
    }

    private var isFreeTier: Bool {
        viewModel.subscriptionTier == "free"
    }

    private func settingsGroup<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title.uppercased())
                .font(ClavisTypography.clavixMono(10, weight: .bold))
                .tracking(0.7)
                .foregroundColor(.clavixInk3)
            ClavixCard(fill: .clavixPaper) {
                VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                    content()
                }
            }
        }
    }

    private func settingsRow<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        HStack {
            Text(title)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(.clavixInk)
            Spacer()
            content()
        }
    }

    private func settingsStaticRow(title: String, value: String) -> some View {
        HStack {
            Text(title)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(.clavixInk)
            Spacer()
            Text(value)
                .font(ClavisTypography.footnote)
                .foregroundColor(.clavixInk3)
        }
    }

    private func settingsActionRow(title: String, destructive: Bool = false, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(destructive ? .clavixBad : .clavixAccent)
        }
        .buttonStyle(.plain)
    }

    private func settingsChevronRow(title: String) -> some View {
        HStack {
            Text(title)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(.clavixInk)
            Spacer()
            Image(systemName: "chevron.right")
                .foregroundColor(.clavixInk3)
        }
    }

    private func toggleRow(title: String, isOn: Binding<Bool>) -> some View {
        HStack {
            Text(title)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(.clavixInk)
            Spacer()
            Button(action: {
                isOn.wrappedValue.toggle()
                Task { await viewModel.saveAlertSettings() }
            }) {
                CX2Toggle(isOn: isOn)
            }
            .buttonStyle(.plain)
        }
    }

    private func linkRow(title: String, urlString: String) -> some View {
        Link(destination: URL(string: urlString)!) {
            HStack {
                Text(title)
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(.clavixInk)
                Spacer()
                Image(systemName: "arrow.up.right")
                    .foregroundColor(.clavixInk3)
            }
        }
    }

    private func selectDigestLength(_ option: SummaryLength) {
        if option == .verbose && isFreeTier {
            showUpgradeSheet = true
            return
        }
        viewModel.summaryLength = option
        Task { await viewModel.saveSummaryLength() }
    }
}

struct SettingsUpgradeSheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    ClavixCard(fill: .clavixPaper) {
                        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                            Text("Upgrade to Pro")
                                .font(ClavisTypography.h2)
                                .foregroundColor(.clavixInk)
                            Text("Verbose digest, brokerage sync, and CSV import are part of Clavix Pro.")
                                .font(ClavisTypography.body)
                                .foregroundColor(.clavixInk3)
                                .fixedSize(horizontal: false, vertical: true)
                            ClavisPrimaryButton(title: "Pro is coming soon", action: { dismiss() })
                        }
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.sectionSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .navigationTitle("Upgrade")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                        .foregroundColor(.clavixInk3)
                }
            }
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
                        .foregroundColor(.clavixInk)

                    Text("Scores range from 0 to 100, where 100 represents minimum risk and 0 represents extreme risk.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.clavixInk3)
                }

                VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                    ScoreBandRow(grade: "AAA", range: "90–100", description: "Investment Grade — minimum risk", color: .gradeCAAA)
                    ScoreBandRow(grade: "AA", range: "80–89", description: "Strong — low risk", color: .gradeCAA)
                    ScoreBandRow(grade: "A", range: "70–79", description: "Sound — moderate-low risk", color: .gradeCA)
                    ScoreBandRow(grade: "BBB", range: "60–69", description: "Adequate — moderate risk", color: .gradeCBBB)
                    ScoreBandRow(grade: "BB", range: "50–59", description: "Speculative — elevated risk", color: .gradeCBB)
                    ScoreBandRow(grade: "B", range: "40–49", description: "Vulnerable — high risk", color: .gradeCB)
                    ScoreBandRow(grade: "CCC", range: "30–39", description: "Weak — very high risk", color: .gradeCCCC)
                    ScoreBandRow(grade: "CC", range: "20–29", description: "Distressed — extreme risk", color: .gradeCCC)
                    ScoreBandRow(grade: "C", range: "10–19", description: "Near Default — severe risk", color: .gradeCC)
                    ScoreBandRow(grade: "F", range: "0–9", description: "Default — critical risk", color: .gradeCF)
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.vertical, ClavisTheme.largeSpacing)
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
            GradeBadge(grade: grade)
            VStack(alignment: .leading, spacing: 2) {
                Text(range)
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(color)
                Text(description)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.clavixInk3)
            }
            Spacer()
        }
        .padding(ClavisTheme.cardPadding)
        .clavisSecondaryCardStyle(fill: .clavixPaper2)
    }
}

struct MethodologyView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.largeSpacing) {
                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                    Text("Methodology Overview")
                        .font(ClavisTypography.sectionTitle)
                        .foregroundColor(.clavixInk)
                    Text("Clavix rates the risk of each tracked ticker across five dimensions. Each dimension is scored from 0 to 100, where higher means lower observed risk.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.clavixInk3)
                }

                VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                    MethodologyStepRow(number: "01", title: "Financial Health", description: "Balance-sheet and cash-flow strength, updated quarterly.")
                    MethodologyStepRow(number: "02", title: "News Sentiment", description: "Seven-day article scoring with recency and source weighting.")
                    MethodologyStepRow(number: "03", title: "Macro Exposure", description: "Observed sensitivity to rates, dollar, crude, VIX, and the S&P 500.")
                    MethodologyStepRow(number: "04", title: "Sector Exposure", description: "Sector beta, sector momentum, sector breadth, and sector-specific news.")
                    MethodologyStepRow(number: "05", title: "Volatility", description: "Realized volatility, volatility ratio, drawdown, and beta.")
                }

                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                    Text("Open any ticker to drill into its full methodology audit.")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.clavixInk4)
                        .padding(ClavisTheme.cardPadding)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .clavisSecondaryCardStyle(fill: .clavixPaper2)
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.vertical, ClavisTheme.largeSpacing)
        }
        .background(ClavisAtmosphereBackground())
        .navigationTitle("Methodology")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func settingsAuditLink(_ title: String) -> some View {
        HStack {
            Text(title)
                .font(ClavisTypography.bodyEmphasis)
                .foregroundColor(.clavixInk)
            Spacer()
            Image(systemName: "chevron.right")
                .foregroundColor(.clavixInk3)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisSecondaryCardStyle(fill: .clavixPaper2)
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
                .foregroundColor(.clavixInk4)
                .frame(width: 24, alignment: .leading)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(.clavixInk)
                Text(description)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.clavixInk3)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisSecondaryCardStyle(fill: .clavixPaper2)
    }
}
