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
                        onSkip: completeAndOpenHoldings,
                        brokerageAvailable: FeatureFlags.brokerageEnabled
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
        VStack(spacing: 0) {
            Spacer(minLength: 40)

            HStack(spacing: 10) {
                Image("clavix_logo")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 32, height: 32)
                    .accessibilityHidden(true)
                Text("CLAVIX")
                    .font(ClavisTypography.clavixMono(20, weight: .bold))
                    .tracking(1.5)
                    .foregroundColor(.clavixInk)
            }
            .frame(maxWidth: .infinity, alignment: .center)
            .padding(.bottom, 32)

            Text("Portfolio risk,\nmeasured.")
                .font(ClavisTypography.clavixSerif(36, weight: .medium))
                .tracking(-0.5)
                .foregroundColor(.clavixInk)
                .multilineTextAlignment(.center)
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(.bottom, 16)

            Text("Clavix scores your positions across five risk dimensions every morning, with the reasoning shown. Not investment advice — risk intelligence.")
                .font(ClavisTypography.inter(15, weight: .regular))
                .foregroundColor(.clavixInk2)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 320)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity, alignment: .center)

            Spacer(minLength: 40)

            ClavixPill(label: "1 of 2", active: true)
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(.bottom, 20)

            OnboardingActionButton(title: "Get started", fill: .clavixInk, foreground: .clavixPaper, action: onContinue)
                .padding(.bottom, 12)

            Button("Sign in with a different account") { onSignIn() }
                .font(ClavisTypography.inter(13, weight: .regular))
                .foregroundColor(.clavixInk3)
                .buttonStyle(.plain)
                .padding(.bottom, 8)
        }
        .padding(.horizontal, 24)
        .padding(.bottom, 32)
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
    var brokerageAvailable: Bool = false

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
            Text("Choose how to add your positions. You can change this at any time from Holdings.")
                .font(ClavisTypography.inter(15, weight: .regular))
                .foregroundColor(.clavixInk2)
                .fixedSize(horizontal: false, vertical: true)

            OnboardingMethodCard(
                title: "Enter manually",
                description: "Add tickers, share count, and cost basis. Takes about 30 seconds.",
                icon: "plus.circle",
                isRecommended: true,
                action: onAddManually
            )

            OnboardingMethodCard(
                title: "Connect your brokerage",
                description: brokerageAvailable ? "Read-only position sync. Clavix never has trading access." : "Automatic sync from your brokerage. Available in a future update.",
                icon: "link",
                badge: brokerageAvailable ? "PRO" : "COMING SOON",
                badgeFill: brokerageAvailable ? Color.clavixAccentSoft : Color.clavixWarnSoft,
                badgeForeground: brokerageAvailable ? Color.clavixAccentInk : Color.clavixWarnInk,
                action: brokerageAvailable ? onConnectBrokerage : nil
            )

            OnboardingMethodCard(
                title: "Upload CSV",
                description: "Import positions from a spreadsheet export. Available in a future update.",
                icon: "doc.text",
                badge: "COMING SOON",
                badgeFill: Color.clavixWarnSoft,
                badgeForeground: Color.clavixWarnInk,
                action: nil
            )

            if let errorMessage = errorMessage?.sanitizedDisplayText, !errorMessage.isEmpty {
                ClavixCard(fill: .clavixBadSoft) {
                    Text(errorMessage)
                        .font(ClavisTypography.inter(14, weight: .regular))
                        .foregroundColor(.clavixBadInk)
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
    var badgeFill: Color = .clavixAccentSoft
    var badgeForeground: Color = .clavixAccentInk
    var isRecommended: Bool = false
    var action: (() -> Void)? = nil

    var isEnabled: Bool { action != nil }

    var body: some View {
        let cardContent = ClavixCard(fill: isEnabled ? .clavixPaper : .clavixPaper2) {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .frame(width: 28)
                    .foregroundColor(isEnabled ? .clavixAccent : .clavixInk4)

                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 8) {
                        Text(title)
                            .font(ClavisTypography.inter(15, weight: .semibold))
                            .foregroundColor(isEnabled ? .clavixInk : .clavixInk3)
                        if isRecommended {
                            Text("RECOMMENDED")
                                .font(ClavisTypography.clavixMono(8, weight: .bold))
                                .foregroundColor(.clavixGoodInk)
                                .padding(.horizontal, 5)
                                .padding(.vertical, 2)
                                .background(Color.clavixGoodSoft)
                                .clipShape(RoundedRectangle(cornerRadius: 3, style: .continuous))
                        }
                        if let badge {
                            Text(badge)
                                .font(ClavisTypography.clavixMono(8, weight: .bold))
                                .foregroundColor(badgeForeground)
                                .padding(.horizontal, 5)
                                .padding(.vertical, 2)
                                .background(badgeFill)
                                .clipShape(RoundedRectangle(cornerRadius: 3, style: .continuous))
                        }
                    }

                    Text(description)
                        .font(ClavisTypography.clavixCaption)
                        .foregroundColor(isEnabled ? .clavixInk2 : .clavixInk3)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer()

                if isEnabled {
                    Image(systemName: "chevron.right")
                        .font(.system(size: 11, weight: .regular))
                        .foregroundColor(.clavixInk4)
                }
            }
        }

        if let action {
            Button(action: action) { cardContent }
                .buttonStyle(.plain)
        } else {
            cardContent
        }
    }
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

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    ClavixInlineNoticeCard(
                        eyebrow: "Coming soon",
                        title: "CSV import is not yet available",
                        message: "You will be able to import positions from a spreadsheet export once this feature launches. For now, add positions manually from the Holdings tab.",
                        footnote: "CSV import will be available for all accounts in a future update.",
                        glyph: "doc.text",
                        fill: .clavixWarnSoft,
                        foreground: .clavixWarnInk,
                        secondary: .clavixWarnInk
                    )
                }
                .padding(.horizontal, ClavixLayout.pad)
                .padding(.top, 24)
            }
            .background(Color.clavixPage.ignoresSafeArea())
            .navigationTitle("Import CSV")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                        .font(ClavisTypography.clavixMono(11, weight: .semibold))
                        .foregroundColor(.clavixAccent)
                }
            }
        }
    }
}

private struct OnboardingUpgradeSheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    ClavixCard(fill: .clavixAccentSoft) {
                        VStack(alignment: .leading, spacing: 10) {
                            ClavixEyebrow("Clavix Pro")
                            Text("Coming soon")
                                .font(ClavisTypography.clavixSerif(26, weight: .medium))
                                .foregroundColor(.clavixInk)
                            Text("Pro will unlock unlimited positions, brokerage sync, verbose morning reports, and deeper risk history.")
                                .font(ClavisTypography.inter(14, weight: .regular))
                                .foregroundColor(.clavixInk2)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }

                    OnboardingActionButton(title: "Got it", fill: .clavixInk, foreground: .clavixPaper, action: { dismiss() })
                }
                .padding(.horizontal, ClavixLayout.pad)
                .padding(.top, 24)
                .padding(.bottom, ClavixLayout.bottomPad)
            }
            .background(Color.clavixPage.ignoresSafeArea())
            .navigationTitle("Clavix Pro")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                        .font(ClavisTypography.clavixMono(11, weight: .semibold))
                        .foregroundColor(.clavixAccent)
                }
            }
        }
    }
}
