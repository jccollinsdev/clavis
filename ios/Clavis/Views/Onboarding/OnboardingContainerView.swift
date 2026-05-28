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

    var body: some View {
        VStack(spacing: 28) {
            Spacer()

            HStack(spacing: 8) {
                Image(systemName: "waveform.path.ecg.rectangle")
                    .font(.system(size: 18, weight: .regular))
                Text("Clavix")
                    .font(ClavisTypography.clavixSerif(19, weight: .semibold))
            }
            .foregroundColor(.clavixInk)

            ClavixEyebrow("Welcome to Clavix")

            Text("Portfolio risk, measured.")
                .font(ClavisTypography.clavixSerif(34, weight: .medium))
                .foregroundColor(.clavixInk)
                .multilineTextAlignment(.center)

            Text("Every morning, Clavix tells you what changed overnight, what it means for your book, and how risky every position actually is, with the math shown.")
                .font(ClavisTypography.inter(15, weight: .regular))
                .foregroundColor(.clavixInk2)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 320)
                .fixedSize(horizontal: false, vertical: true)

            Spacer()

            ClavixPill(label: "1 of 2", active: true)

            OnboardingActionButton(title: "Get started", fill: .clavixInk, foreground: .clavixPaper, action: onContinue)

            Button("Sign in") { onSignIn() }
                .font(ClavisTypography.inter(14, weight: .semibold))
                .foregroundColor(.clavixInk3)
                .buttonStyle(.plain)
        }
        .padding(24)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.clavixPage)
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
        ClavixScreen(
            eyebrow: "Step 2 of 2",
            title: "Add portfolio",
            trailing: AnyView(
                Button("Back", action: onBack)
                    .font(ClavisTypography.clavixMono(10, weight: .semibold))
                    .foregroundColor(.clavixAccent)
                    .buttonStyle(.plain)
            )
        ) {
            Text("Choose how Clavix should read your positions.")
                .font(ClavisTypography.clavixSerif(20, weight: .medium))
                .foregroundColor(.clavixInk)

            OnboardingMethodCard(
                title: "Connect your brokerage",
                description: "Read-only position sync for Pro accounts.",
                icon: "link",
                badge: "PRO",
                detail: "Clavix never has trading access.",
                action: onConnectBrokerage
            )
            OnboardingMethodCard(
                title: "Enter manually",
                description: "Ticker, share count, and cost basis.",
                icon: "plus",
                action: onAddManually
            )
            OnboardingMethodCard(
                title: "Upload CSV",
                description: isFreeTier ? "Coming soon for Pro accounts." : "Map rows from a portfolio export.",
                icon: "doc",
                badge: "PRO",
                action: onImportCSV
            )

            if let errorMessage = errorMessage?.sanitizedDisplayText, !errorMessage.isEmpty {
                ClavixCard(fill: .clavixBadSoft) {
                    Text(errorMessage)
                        .font(ClavisTypography.inter(14, weight: .regular))
                        .foregroundColor(.clavixInk2)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

            if isCompleting {
                ProgressView()
                    .tint(.clavixInk)
                    .frame(maxWidth: .infinity, alignment: .center)
            }

            OnboardingActionButton(
                title: "Continue manually",
                fill: .clavixInk,
                foreground: .clavixPaper,
                isEnabled: !isCompleting,
                action: onAddManually
            )

            Button("Skip for now", action: onSkip)
                .font(ClavisTypography.clavixCaption)
                .foregroundColor(.clavixInk3)
                .buttonStyle(.plain)
                .frame(maxWidth: .infinity, alignment: .center)
        }
    }
}

private struct OnboardingMethodCard: View {
    let title: String
    let description: String
    let icon: String
    var badge: String? = nil
    var detail: String? = nil
    let action: () -> Void

    var bodyView: some View {
        Button(action: action) {
            ClavixCard {
                HStack(spacing: 12) {
                    Image(systemName: icon)
                        .frame(width: 28)
                        .foregroundColor(.clavixAccent)

                    VStack(alignment: .leading, spacing: 4) {
                        HStack(spacing: 8) {
                            Text(title)
                                .font(ClavisTypography.inter(15, weight: .semibold))
                                .foregroundColor(.clavixInk)
                            if let badge {
                                Text(badge)
                                    .font(ClavisTypography.clavixMono(9, weight: .bold))
                                    .foregroundColor(.clavixAccentInk)
                                    .padding(.horizontal, 5)
                                    .padding(.vertical, 2)
                                    .background(Color.clavixAccentSoft)
                                    .clipShape(RoundedRectangle(cornerRadius: 3, style: .continuous))
                            }
                        }

                        Text(description)
                            .font(ClavisTypography.clavixCaption)
                            .foregroundColor(.clavixInk2)
                            .fixedSize(horizontal: false, vertical: true)

                        if let detail {
                            Text(detail)
                                .font(ClavisTypography.clavixCaption)
                                .foregroundColor(.clavixInk3)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }

                    Spacer()

                    Image(systemName: "chevron.right")
                        .font(.system(size: 11, weight: .regular))
                        .foregroundColor(.clavixInk4)
                }
            }
        }
        .buttonStyle(.plain)
    }

    var body: some View { bodyView }
}

private struct OnboardingActionButton: View {
    let title: String
    let fill: Color
    let foreground: Color
    var isEnabled: Bool = true
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(ClavisTypography.inter(15, weight: .semibold))
                .foregroundColor(isEnabled ? foreground : .clavixInk4)
                .frame(maxWidth: .infinity)
                .frame(height: 48)
                .background(fill)
                .clipShape(RoundedRectangle(cornerRadius: ClavixLayout.controlRadius, style: .continuous))
                .opacity(isEnabled ? 1 : 0.7)
        }
        .buttonStyle(.plain)
        .disabled(!isEnabled)
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

                    ClavisStandardCard(fill: .clavixPaper) {
                        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                            Text("Preview")
                                .font(ClavisTypography.label)
                                .foregroundColor(.clavixInk3)
                            ForEach(Array(previewRows.enumerated()), id: \.offset) { _, row in
                                Text(row.joined(separator: " · "))
                                    .font(ClavisTypography.footnote)
                                    .foregroundColor(.clavixInk3)
                            }
                        }
                    }

                    ClavisStandardCard(fill: .clavixPaper2) {
                        // TODO: wire CSV import to a backend parsing endpoint once it exists.
                        Text("Importing... we'll notify you when done")
                            .font(ClavisTypography.body)
                            .foregroundColor(.clavixInk3)
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
                        .foregroundColor(.clavixInk3)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Import \(previewRows.count) positions") { }
                        .foregroundColor(.clavixAccent)
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
        ClavisStandardCard(fill: .clavixPaper) {
            HStack {
                Text(label)
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(.clavixInk)
                Spacer()
                Menu(selection.wrappedValue) {
                    Button("Ticker") { selection.wrappedValue = "Ticker" }
                    Button("Shares") { selection.wrappedValue = "Shares" }
                    Button("Cost Basis") { selection.wrappedValue = "Cost Basis" }
                    Button("Date") { selection.wrappedValue = "Date" }
                }
                .font(ClavisTypography.footnote)
                .foregroundColor(.clavixInk3)
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
                    ClavisStandardCard(fill: .clavixPaper) {
                        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                            Text("Upgrade to Pro")
                                .font(ClavisTypography.h2)
                                .foregroundColor(.clavixInk)
                            Text("Connect your brokerage and import CSV files with Clavix Pro.")
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
