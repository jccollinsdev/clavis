import SwiftUI
import UniformTypeIdentifiers

struct OnboardingContainerView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @StateObject private var viewModel = OnboardingViewModel()
    @StateObject private var brokerageViewModel = BrokerageViewModel()
    @State private var showUpgradeSheet = false
    @State private var showCSVSheet = false

    var body: some View {
        ZStack {
            Color.clavixPage.ignoresSafeArea()

            Group {
                switch viewModel.currentPage {
                case .welcome:
                    OnboardingWelcomeView(
                        onContinue: { viewModel.nextPage() },
                        onSignIn: { Task { await authViewModel.signOut() } }
                    )
                case .addPortfolio:
                    OnboardingAddPortfolioView(
                        isFreeTier: authViewModel.subscriptionTier.lowercased() == "free",
                        isCompleting: viewModel.isCompleting,
                        errorMessage: viewModel.errorMessage ?? brokerageViewModel.errorMessage,
                        onBack: { viewModel.previousPage() },
                        onConnectBrokerage: handleConnectBrokerage,
                        onImportCSV: { showCSVSheet = true },
                        onAddManually: completeAndOpenHoldings,
                        onSkip: completeAndOpenHoldings
                    )
                }
            }
            .animation(.easeInOut(duration: 0.2), value: viewModel.currentPage)
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
        .sheet(isPresented: $showCSVSheet) {
            if authViewModel.subscriptionTier.lowercased() == "free" {
                OnboardingUpgradeSheet()
            } else {
                CSVImportSheet()
            }
        }
        .sheet(isPresented: $showUpgradeSheet) {
            OnboardingUpgradeSheet()
        }
        .onReceive(NotificationCenter.default.publisher(for: .snapTradeCallbackReceived)) { notification in
            guard let url = notification.object as? URL else { return }
            Task { await brokerageViewModel.handleCallback(url: url) }
        }
        .preferredColorScheme(.light)
    }

    private func handleConnectBrokerage() {
        if authViewModel.subscriptionTier.lowercased() == "free" {
            showUpgradeSheet = true
            return
        }

        Task {
            await brokerageViewModel.startConnect()
        }
    }

    private func completeAndOpenHoldings() {
        viewModel.completeOnboarding {
            authViewModel.markOnboardingComplete()
            UserDefaults.standard.set(1, forKey: "clavix.selectedTab")
            NotificationCenter.default.post(name: .openAddHoldingFromOnboarding, object: nil)
        }
    }
}

private struct OnboardingWelcomeView: View {
    let onContinue: () -> Void
    let onSignIn: () -> Void

    private let bullets: [(String, String)] = [
        ("One morning briefing, tailored to your holdings", "Read 4-6 apps to piece together overnight news"),
        ("Pre-translated: macro → sector → your positions, in order", "Manually translate macro news into \"what does this mean for me\""),
        ("See every article, every formula, every input that produced every score", "Trust an opaque \"AI risk score\" from a fintech app")
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Spacer(minLength: 40)

            VStack(alignment: .leading, spacing: 28) {
                Text("CLAVIX")
                    .font(ClavisTypography.clavixMono(11, weight: .bold))
                    .tracking(4)
                    .foregroundColor(.clavixAccent)

                VStack(alignment: .leading, spacing: 14) {
                    Text("Portfolio risk, measured.")
                        .font(ClavisTypography.clavixSerif(32, weight: .medium))
                        .foregroundColor(.clavixInk)

                    Text("Clavix tells you what happened to your portfolio overnight, what it means, and how risky every position you own actually is — with the math shown.")
                        .font(ClavisTypography.clavixSerif(15))
                        .foregroundColor(.clavixInk2)
                        .fixedSize(horizontal: false, vertical: true)
                }

                VStack(alignment: .leading, spacing: 16) {
                    ForEach(Array(bullets.enumerated()), id: \.offset) { index, bullet in
                        HStack(alignment: .top, spacing: 12) {
                            Text("\(index + 1)")
                                .font(ClavisTypography.clavixMono(11, weight: .bold))
                                .foregroundColor(.clavixInk)
                                .frame(width: 28, height: 28)
                                .background(Color.surface)
                                .overlay(Rectangle().stroke(Color.border, lineWidth: 1))

                            VStack(alignment: .leading, spacing: 4) {
                                Text(bullet.0)
                                    .font(ClavisTypography.bodyEmphasis)
                                    .foregroundColor(.textPrimary)
                                Text(bullet.1)
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textSecondary)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                }
            }
            .padding(.horizontal, 24)

            Spacer()

            VStack(spacing: 10) {
                ClavisPrimaryButton(title: "Get Started", action: onContinue)
                Button("Sign in") { onSignIn() }
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.textSecondary)
                    .buttonStyle(.plain)
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 32)
        }
    }
}

private struct OnboardingAddPortfolioView: View {
    let isFreeTier: Bool
    let isCompleting: Bool
    let errorMessage: String?
    let onBack: () -> Void
    let onConnectBrokerage: () -> Void
    let onImportCSV: () -> Void
    let onAddManually: () -> Void
    let onSkip: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Button(action: onBack) {
                    Image(systemName: "chevron.left")
                        .foregroundColor(.textSecondary)
                }
                .buttonStyle(.plain)
                Spacer()
                Button("Skip for now", action: onSkip)
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.textSecondary)
                    .buttonStyle(.plain)
            }
            .padding(.horizontal, 24)
            .padding(.top, 24)

            VStack(alignment: .leading, spacing: 12) {
                Text("How would you like to add your portfolio?")
                    .font(ClavisTypography.h1)
                    .foregroundColor(.textPrimary)
                Text("Choose the path that fits how you already track your book.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }
            .padding(.horizontal, 24)
            .padding(.top, 28)

            VStack(spacing: 12) {
                pathCard(title: "Connect Brokerage", subtitle: "Sync automatically", badge: "Pro", isRecommended: true, action: onConnectBrokerage)
                pathCard(title: "Import CSV", subtitle: "Upload from your brokerage", badge: "Pro", isRecommended: false, action: onImportCSV)
                pathCard(title: "Add Manually", subtitle: "Enter positions yourself", badge: "Free", isRecommended: false, action: onAddManually)
            }
            .padding(.horizontal, 16)
            .padding(.top, 24)

            if let errorMessage {
                Text(errorMessage)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.bad)
                    .padding(.horizontal, 24)
                    .padding(.top, 12)
            }

            Spacer()

            if isCompleting {
                ProgressView()
                    .tint(.textPrimary)
                    .frame(maxWidth: .infinity)
                    .padding(.bottom, 24)
            }
        }
        .background(Color.backgroundPrimary)
    }

    private func pathCard(title: String, subtitle: String, badge: String, isRecommended: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(title)
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.textPrimary)
                    Spacer()
                    Text(badge)
                        .font(ClavisTypography.label)
                        .foregroundColor(badge == "Pro" ? .accentBurnt : .textSecondary)
                }
                Text(subtitle)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
                if isRecommended {
                    Text("Recommended")
                        .font(ClavisTypography.label)
                        .foregroundColor(.accentBurnt)
                }
                if title == "Connect Brokerage" {
                    Text("Read-only sync through your brokerage. Clavix never has trading access.")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(ClavisTheme.cardPadding)
            .background(Color.surface)
            .overlay(Rectangle().stroke(Color.border, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }
}

private struct CSVImportSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var showImporter = false
    @State private var selectedFileName: String?
    @State private var previewRows: [[String]] = [
        ["AAPL", "100", "182.45", "2025-01-15"],
        ["MSFT", "50", "401.10", "2024-11-03"],
        ["NVDA", "24", "731.22", "2024-08-12"]
    ]
    @State private var tickerColumn = "Ticker"
    @State private var sharesColumn = "Shares"
    @State private var costBasisColumn = "Cost Basis"
    @State private var dateColumn = "Date"

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    ClavisPrimaryButton(title: selectedFileName == nil ? "Choose CSV" : selectedFileName!, action: { showImporter = true })

                    mappingRow(label: "Ticker", selection: $tickerColumn)
                    mappingRow(label: "Shares", selection: $sharesColumn)
                    mappingRow(label: "Cost Basis", selection: $costBasisColumn)
                    mappingRow(label: "Date", selection: $dateColumn)

                    ClavisStandardCard(fill: .surface) {
                        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                            Text("Preview")
                                .font(ClavisTypography.label)
                                .foregroundColor(.textSecondary)
                            ForEach(Array(previewRows.enumerated()), id: \.offset) { _, row in
                                Text(row.joined(separator: " · "))
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.textSecondary)
                            }
                        }
                    }

                    ClavisStandardCard(fill: .surfaceElevated) {
                        // TODO: wire CSV import to a backend parsing endpoint once it exists.
                        Text("Importing... we'll notify you when done")
                            .font(ClavisTypography.body)
                            .foregroundColor(.textSecondary)
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.sectionSpacing)
            }
            .background(ClavisAtmosphereBackground())
            .navigationTitle("Import CSV")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                        .foregroundColor(.textSecondary)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Import \(previewRows.count) positions") { }
                        .foregroundColor(.accentBurnt)
                }
            }
            .fileImporter(isPresented: $showImporter, allowedContentTypes: [.commaSeparatedText, .plainText]) { result in
                if case .success(let url) = result {
                    selectedFileName = url.lastPathComponent
                    if let content = try? String(contentsOf: url) {
                        let lines = content.split(whereSeparator: \.isNewline).prefix(5)
                        let rows = lines.map { line in
                            line.split(separator: ",").map { String($0) }
                        }
                        if !rows.isEmpty {
                            previewRows = rows
                        }
                    }
                }
            }
        }
    }

    private func mappingRow(label: String, selection: Binding<String>) -> some View {
        ClavisStandardCard(fill: .surface) {
            HStack {
                Text(label)
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(.textPrimary)
                Spacer()
                Menu(selection.wrappedValue) {
                    Button("Ticker") { selection.wrappedValue = "Ticker" }
                    Button("Shares") { selection.wrappedValue = "Shares" }
                    Button("Cost Basis") { selection.wrappedValue = "Cost Basis" }
                    Button("Date") { selection.wrappedValue = "Date" }
                }
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
            }
        }
    }
}

private struct OnboardingUpgradeSheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    ClavisStandardCard(fill: .surface) {
                        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                            Text("Upgrade to Pro")
                                .font(ClavisTypography.h2)
                                .foregroundColor(.textPrimary)
                            Text("Connect your brokerage and import CSV files with Clavix Pro.")
                                .font(ClavisTypography.body)
                                .foregroundColor(.textSecondary)
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
                        .foregroundColor(.textSecondary)
                }
            }
        }
    }
}
