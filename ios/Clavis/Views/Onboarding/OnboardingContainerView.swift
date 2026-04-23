import SwiftUI

struct OnboardingContainerView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @StateObject private var viewModel = OnboardingViewModel()
    @StateObject private var brokerageViewModel = BrokerageViewModel()

    var body: some View {
        ZStack {
            Color.backgroundPrimary.ignoresSafeArea()

            VStack(alignment: .leading, spacing: 0) {
                OnboardingProgressHeader(
                    currentPage: viewModel.currentPage.rawValue + 1,
                    totalPages: OnboardingPage.allCases.count
                )
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, 24)

                Group {
                    switch viewModel.currentPage {
                    case .welcome:
                        WelcomeStepView(viewModel: viewModel)
                    case .nameDOB:
                        DateOfBirthStepView(viewModel: viewModel)
                    case .riskAck:
                        RiskAcknowledgmentView(viewModel: viewModel)
                    case .preferences:
                        OnboardingPreferencesView(viewModel: viewModel) {
                            viewModel.nextPage()
                        }
                    case .brokerage:
                        OnboardingBrokerageView(
                            viewModel: viewModel,
                            brokerageViewModel: brokerageViewModel
                        ) {
                            viewModel.completeOnboarding {
                                authViewModel.markOnboardingComplete()
                            }
                        }
                    }
                }
                .transition(.opacity)
                .animation(.easeInOut(duration: 0.2), value: viewModel.currentPage)
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
        .preferredColorScheme(.dark)
        .ignoresSafeArea(.keyboard, edges: .bottom)
    }
}

enum OnboardingPage: Int, CaseIterable {
    case welcome = 0
    case nameDOB = 1
    case riskAck = 2
    case preferences = 3
    case brokerage = 4
}

private struct OnboardingProgressHeader: View {
    let currentPage: Int
    let totalPages: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 4) {
                ForEach(0..<totalPages, id: \.self) { index in
                    RoundedRectangle(cornerRadius: 2, style: .continuous)
                        .fill(index < currentPage ? Color.textPrimary : Color.border)
                        .frame(maxWidth: .infinity)
                        .frame(height: 3)
                }
            }

            Text("Step \(currentPage) of \(totalPages)")
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)
        }
    }
}

private struct WelcomeStepView: View {
    @ObservedObject var viewModel: OnboardingViewModel
    @FocusState private var isNameFocused: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Spacer(minLength: 28)

            VStack(alignment: .leading, spacing: 24) {
                ZStack {
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .fill(Color.surface)
                        .overlay(
                            RoundedRectangle(cornerRadius: 16, style: .continuous)
                                .stroke(Color.border, lineWidth: 1)
                        )
                        .frame(width: 64, height: 64)

                    Text("C")
                        .font(.system(size: 30, weight: .bold, design: .monospaced))
                        .foregroundColor(.textPrimary)
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text("Portfolio risk,\nmeasured.")
                        .font(.system(size: 30, weight: .bold))
                        .foregroundColor(.textPrimary)

                    Text("Clavix helps you answer three questions every morning: how risky is my portfolio, what changed, and what should I look at first.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                OnboardingInputField(
                    label: "YOUR NAME",
                    text: $viewModel.name,
                    placeholder: "First name",
                    keyboardType: .default
                )
                .focused($isNameFocused)
            }
            .padding(.horizontal, ClavisTheme.screenPadding)

            Spacer()

            OnboardingPrimaryButton(title: "Get started") {
                viewModel.nextPage()
            }
            .disabled(viewModel.name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.bottom, 36)
        }
        .onAppear {
            isNameFocused = viewModel.name.isEmpty
        }
    }
}

private struct DateOfBirthStepView: View {
    @ObservedObject var viewModel: OnboardingViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Spacer(minLength: 24)

            VStack(alignment: .leading, spacing: 24) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Date of birth")
                        .font(ClavisTypography.h1)
                        .foregroundColor(.textPrimary)

                    Text("Required to confirm you meet minimum age requirements in your jurisdiction.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                DatePicker(
                    "Date of birth",
                    selection: $viewModel.dateOfBirth,
                    in: ...maxAllowedDate,
                    displayedComponents: .date
                )
                .datePickerStyle(.compact)
                .labelsHidden()

                Text(viewModel.dateOfBirth.formatted(date: .abbreviated, time: .omitted))
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)

                VStack(alignment: .leading, spacing: 8) {
                    Text("You must be at least 18 years old to use Clavix. We currently use this only to derive age verification and store the birth year in your profile.")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .padding(12)
                .clavisSecondaryCardStyle(fill: .surfaceElevated)
            }
            .padding(.horizontal, ClavisTheme.screenPadding)

            Spacer()

            VStack(spacing: 10) {
                OnboardingPrimaryButton(title: "Continue") {
                    viewModel.nextPage()
                }
                .disabled(!viewModel.isValidDateOfBirth(viewModel.dateOfBirth))

                OnboardingSecondaryButton(title: "Back") {
                    viewModel.previousPage()
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.bottom, 36)
        }
    }

    private var maxAllowedDate: Date {
        Calendar.current.date(byAdding: .year, value: -18, to: Date()) ?? Date()
    }
}

struct RiskAcknowledgmentView: View {
    @ObservedObject var viewModel: OnboardingViewModel
    @State private var hasAcknowledged = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("One thing before we begin.")
                        .font(ClavisTypography.h1)
                        .foregroundColor(.textPrimary)

                    Text(ClavisCopy.informationalDisclosure)
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                OnboardingNoticeCard {
                    Text("Risk acknowledgement")
                        .font(ClavisTypography.label)
                        .foregroundColor(.textSecondary)

                    Text(ClavisCopy.riskAcknowledgment)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)

                    Divider()
                        .overlay(Color.border)

                    Text("Past scores do not predict future results. Always consult a qualified adviser before making investment decisions.")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                }

                Button {
                    hasAcknowledged.toggle()
                } label: {
                    HStack(alignment: .top, spacing: 12) {
                        RoundedRectangle(cornerRadius: 5, style: .continuous)
                            .stroke(hasAcknowledged ? Color.informational : Color.border, lineWidth: 1.5)
                            .background(
                                RoundedRectangle(cornerRadius: 5, style: .continuous)
                                    .fill(hasAcknowledged ? Color.informational : Color.clear)
                            )
                            .frame(width: 22, height: 22)
                            .overlay(
                                Image(systemName: "checkmark")
                                    .font(.system(size: 15, weight: .bold))
                                    .foregroundColor(.white)
                                    .opacity(hasAcknowledged ? 1 : 0)
                            )

                        Text("I understand Clavix provides information only, and that I am solely responsible for my investment decisions.")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textSecondary)
                            .multilineTextAlignment(.leading)
                    }
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.top, 24)

            VStack(spacing: 10) {
                OnboardingPrimaryButton(title: "Agree & continue") {
                    viewModel.nextPage()
                }
                .disabled(!hasAcknowledged)

                OnboardingSecondaryButton(title: "Back") {
                    viewModel.previousPage()
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.bottom, 36)
        }
    }
}

struct OnboardingPreferencesView: View {
    @ObservedObject var viewModel: OnboardingViewModel
    let onContinue: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Spacer(minLength: 24)

            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Pick what wakes you up.")
                        .font(ClavisTypography.h1)
                        .foregroundColor(.textPrimary)

                    Text("Adjust any of these later in Settings.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }

                VStack(spacing: 10) {
                    OnboardingToggleCard(
                        title: "Morning digest",
                        subtitle: "Daily portfolio summary at your configured digest time",
                        isOn: $viewModel.morningDigestEnabled
                    )

                    OnboardingToggleCard(
                        title: "Grade changes",
                        subtitle: "Any upgrade or downgrade in your holdings",
                        isOn: $viewModel.alertsGradeChangesEnabled
                    )

                    OnboardingToggleCard(
                        title: "Major events",
                        subtitle: "Earnings, regulatory actions, and major news",
                        isOn: $viewModel.alertsMajorEventsEnabled
                    )

                    OnboardingToggleCard(
                        title: "Large price moves",
                        subtitle: "Significant daily moves across your portfolio",
                        isOn: $viewModel.alertsLargePriceMovesEnabled
                    )
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)

            Spacer()

            if let errorMessage = viewModel.errorMessage {
                Text(errorMessage)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.riskF)
                    .padding(.horizontal, ClavisTheme.screenPadding)
                    .padding(.bottom, 8)
            }

            VStack(spacing: 10) {
                OnboardingPrimaryButton(title: "Continue") {
                    onContinue()
                }

                OnboardingSecondaryButton(title: "Back") {
                    viewModel.previousPage()
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.bottom, 36)
        }
    }
}

struct OnboardingBrokerageView: View {
    @ObservedObject var viewModel: OnboardingViewModel
    @ObservedObject var brokerageViewModel: BrokerageViewModel
    let onComplete: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Spacer(minLength: 24)

            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Connect your brokerage")
                        .font(ClavisTypography.h1)
                        .foregroundColor(.textPrimary)

                    Text("Optional. SnapTrade keeps this read-only and only imports holdings so Clavix can replace manual entry.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                OnboardingNoticeCard {
                    Text(brokerageViewModel.isConnected ? "Brokerage connected" : "Why connect now?")
                        .font(ClavisTypography.label)
                        .foregroundColor(.textSecondary)

                    if let connection = brokerageViewModel.primaryConnection {
                        Text(connection.institutionName ?? "Connected brokerage")
                            .font(ClavisTypography.bodyEmphasis)
                            .foregroundColor(.textPrimary)
                    }

                    Text(brokerageViewModel.isConnected
                         ? "Your holdings can now sync into Clavix. You can switch between manual and automatic sync later in Settings."
                         : "Importing holdings here is faster than typing positions by hand, and you can still keep manual positions alongside synced ones.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }

                if let infoMessage = brokerageViewModel.infoMessage {
                    Text(infoMessage)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.informational)
                }

                if let errorMessage = brokerageViewModel.errorMessage {
                    Text(errorMessage)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.riskF)
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)

            Spacer()

            VStack(spacing: 10) {
                if brokerageViewModel.isConnected {
                    OnboardingPrimaryButton(title: viewModel.isCompleting ? "Opening Clavix..." : "Open Clavix") {
                        onComplete()
                    }
                    .disabled(viewModel.isCompleting)

                    OnboardingSecondaryButton(title: brokerageViewModel.isSyncing ? "Syncing..." : "Sync holdings now") {
                        Task { await brokerageViewModel.syncNow(refreshRemote: true) }
                    }
                    .disabled(brokerageViewModel.isSyncing || viewModel.isCompleting)
                } else {
                    OnboardingPrimaryButton(title: "Connect brokerage") {
                        Task {
                            await brokerageViewModel.startConnect(
                                reconnectConnectionId: brokerageViewModel.primaryConnection?.disabled == true ? brokerageViewModel.primaryConnection?.id : nil
                            )
                        }
                    }

                    OnboardingSecondaryButton(title: viewModel.isCompleting ? "Opening Clavix..." : "I'll add manually for now") {
                        onComplete()
                    }
                    .disabled(viewModel.isCompleting)
                }

                OnboardingSecondaryButton(title: "Back") {
                    viewModel.previousPage()
                }
                .disabled(viewModel.isCompleting)
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.bottom, 36)
        }
        .task {
            if brokerageViewModel.status == nil {
                await brokerageViewModel.loadStatus()
            }
        }
    }
}

private struct OnboardingNoticeCard<Content: View>: View {
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            content
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

private struct OnboardingToggleCard: View {
    let title: String
    let subtitle: String
    @Binding var isOn: Bool

    var body: some View {
        Button {
            isOn.toggle()
        } label: {
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 14) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(title)
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(.textPrimary)

                        Text(subtitle)
                            .font(.system(size: 12, weight: .regular))
                            .foregroundColor(.textSecondary)
                    }

                    Spacer()

                    CX2Toggle(isOn: $isOn)
                }
            }
        }
        .buttonStyle(.plain)
        .padding(14)
        .clavisCardStyle(fill: .surface)
    }
}

private struct OnboardingInputField: View {
    let label: String
    @Binding var text: String
    let placeholder: String
    let keyboardType: UIKeyboardType
    var monospaced: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(label)
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)

            TextField(placeholder, text: $text)
                .textFieldStyle(ClavisTextFieldStyle(monospaced: monospaced))
                .keyboardType(keyboardType)
                .textContentType(.none)
                .autocorrectionDisabled()
        }
    }
}

private struct OnboardingPrimaryButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 16, weight: .semibold))
                .frame(maxWidth: .infinity)
                .padding(.vertical, 15)
                .background(Color.textPrimary)
                .foregroundColor(.backgroundPrimary)
                .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
        }
        .buttonStyle(.plain)
    }
}

private struct OnboardingSecondaryButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 15, weight: .regular))
                .foregroundColor(.textSecondary)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
        }
        .buttonStyle(.plain)
    }
}

struct ClavisTextFieldStyle: TextFieldStyle {
    var monospaced: Bool = false

    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .font(monospaced ? .system(size: 15, weight: .regular, design: .monospaced) : .system(size: 15, weight: .regular))
            .padding(13)
            .background(Color.surfaceElevated)
            .foregroundColor(.textPrimary)
            .overlay(
                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                    .stroke(Color.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous))
    }
}
