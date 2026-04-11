import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @StateObject private var viewModel = SettingsViewModel()
    @State private var hasLoaded = false

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                    AccountSection(
                        userEmail: viewModel.userEmail,
                        onSignOut: {
                            Task { await authViewModel.signOut() }
                        }
                    )

                    DigestSection(
                        digestTime: $viewModel.digestTime,
                        summaryLength: $viewModel.summaryLength,
                        weekdayOnly: $viewModel.weekdayOnly,
                        onDigestTimeChange: { Task { await viewModel.saveDigestTime() } },
                        onSummaryLengthChange: { Task { await viewModel.saveSummaryLength() } },
                        onWeekdayOnlyChange: { Task { await viewModel.saveWeekdayOnly() } }
                    )

                    AlertsSection(
                        alertsGradeChanges: $viewModel.alertsGradeChanges,
                        alertsMajorEvents: $viewModel.alertsMajorEvents,
                        alertsPortfolioRisk: $viewModel.alertsPortfolioRisk,
                        quietHoursEnabled: $viewModel.quietHoursEnabled,
                        quietHoursStart: $viewModel.quietHoursStart,
                        quietHoursEnd: $viewModel.quietHoursEnd,
                        onAlertSettingsChange: { Task { await viewModel.saveAlertSettings() } }
                    )

                    AboutSection()
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.largeSpacing)
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.large)
            .background(ClavisAtmosphereBackground())
            .onAppear {
                guard !hasLoaded else { return }
                hasLoaded = true
                Task { await viewModel.load() }
            }
        }
    }
}

struct AccountSection: View {
    let userEmail: String
    let onSignOut: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            Text("Account")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            LabeledContent("Email", value: userEmail)
                .foregroundColor(.textSecondary)

            Button("Sign Out", role: .destructive, action: onSignOut)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle()
    }
}

struct DigestSection: View {
    @Binding var digestTime: Date
    @Binding var summaryLength: SummaryLength
    @Binding var weekdayOnly: Bool
    let onDigestTimeChange: () -> Void
    let onSummaryLengthChange: () -> Void
    let onWeekdayOnlyChange: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            Text("Digest")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            HStack {
                Text("Daily Digest Time")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
                Spacer()
                DatePicker("", selection: $digestTime, displayedComponents: .hourAndMinute)
                    .labelsHidden()
                    .onChange(of: digestTime) { _, _ in onDigestTimeChange() }
            }

            VStack(alignment: .leading, spacing: ClavisTheme.microSpacing) {
                Text("Summary Length")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)

                Picker("Summary Length", selection: $summaryLength) {
                    ForEach(SummaryLength.allCases, id: \.self) { length in
                        Text(length.rawValue).tag(length)
                    }
                }
                .pickerStyle(.segmented)
                .onChange(of: summaryLength) { _, _ in onSummaryLengthChange() }
            }

            Toggle("Weekday Only", isOn: $weekdayOnly)
                .onChange(of: weekdayOnly) { _, _ in onWeekdayOnlyChange() }

            Text("Changes are saved automatically.")
                .font(ClavisTypography.footnote)
                .foregroundColor(.textSecondary)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle()
    }
}

struct AlertsSection: View {
    @Binding var alertsGradeChanges: Bool
    @Binding var alertsMajorEvents: Bool
    @Binding var alertsPortfolioRisk: Bool
    @Binding var quietHoursEnabled: Bool
    @Binding var quietHoursStart: Date
    @Binding var quietHoursEnd: Date
    let onAlertSettingsChange: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            Text("Alerts")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            Toggle("Grade Changes", isOn: $alertsGradeChanges)
                .onChange(of: alertsGradeChanges) { _, _ in onAlertSettingsChange() }

            Toggle("Major Events", isOn: $alertsMajorEvents)
                .onChange(of: alertsMajorEvents) { _, _ in onAlertSettingsChange() }

            Toggle("Portfolio Risk Changes", isOn: $alertsPortfolioRisk)
                .onChange(of: alertsPortfolioRisk) { _, _ in onAlertSettingsChange() }

            Toggle("Quiet Hours", isOn: $quietHoursEnabled)
                .onChange(of: quietHoursEnabled) { _, _ in onAlertSettingsChange() }

            if quietHoursEnabled {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("From")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textTertiary)
                        DatePicker("", selection: $quietHoursStart, displayedComponents: .hourAndMinute)
                            .labelsHidden()
                    }

                    Spacer()

                    VStack(alignment: .leading, spacing: 2) {
                        Text("To")
                            .font(ClavisTypography.footnote)
                            .foregroundColor(.textTertiary)
                        DatePicker("", selection: $quietHoursEnd, displayedComponents: .hourAndMinute)
                            .labelsHidden()
                    }
                }
                .onChange(of: quietHoursStart) { _, _ in onAlertSettingsChange() }
                .onChange(of: quietHoursEnd) { _, _ in onAlertSettingsChange() }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle()
    }
}

struct AboutSection: View {
    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
            Text("About")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            LabeledContent("Version", value: "1.0.0")

            NavigationLink(destination: ScoreExplanationView()) {
                HStack {
                    Text("Score Explanation")
                        .foregroundColor(.textPrimary)
                    Spacer()
                    Image(systemName: "chevron.right")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(.textTertiary)
                }
            }

            NavigationLink(destination: MethodologyView()) {
                HStack {
                    Text("Methodology Overview")
                        .foregroundColor(.textPrimary)
                    Spacer()
                    Image(systemName: "chevron.right")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(.textTertiary)
                }
            }

            Link("Privacy Policy", destination: URL(string: "https://clavis.app/privacy")!)
            Link("Terms of Service", destination: URL(string: "https://clavis.app/terms")!)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle()
    }
}

struct ScoreExplanationView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Text("How Risk Scores Work")
                    .font(ClavisTypography.sectionTitle)
                    .foregroundColor(.textPrimary)

                Text("Scores range from 0 to 100, where 100 represents minimum risk and 0 represents extreme risk.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }
            .padding()
        }
        .navigationTitle("Score Explanation")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct MethodologyView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                Text("Methodology Overview")
                    .font(ClavisTypography.sectionTitle)
                    .foregroundColor(.textPrimary)

                Text("Clavis evaluates positions across multiple risk dimensions including market structure, macro sensitivity, sentiment, and catalyst quality.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
            }
            .padding()
        }
        .navigationTitle("Methodology")
        .navigationBarTitleDisplayMode(.inline)
    }
}
