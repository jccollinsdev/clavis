import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var authViewModel: AuthViewModel
    @Binding var selectedTab: Int
    @StateObject private var viewModel = SettingsViewModel()
    @State private var hasLoaded = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ClavisTopBar(onLogoTap: { selectedTab = 0 }) {
                    Button {
                        selectedTab = 1
                    } label: {
                        Label("Holdings", systemImage: "briefcase.fill")
                    }

                    Button {
                        selectedTab = 2
                    } label: {
                        Label("Digest", systemImage: "newspaper.fill")
                    }

                    Button {
                        selectedTab = 3
                    } label: {
                        Label("Alerts", systemImage: "bell.fill")
                    }

                    Button {
                        selectedTab = 4
                    } label: {
                        Label("Settings", systemImage: "gearshape.fill")
                    }

                    Divider()

                    Button {
                        Task { await authViewModel.signOut() }
                    } label: {
                        Label("Sign Out", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.top, 8)
                .padding(.bottom, 12)

                ScrollView {
                    LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                        BrandSection()

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
                    .padding(.top, ClavisTheme.largeSpacing)
                    .padding(.bottom, ClavisTheme.extraLargeSpacing)
                }
            }
            .background(ClavisAtmosphereBackground())
            .toolbar(.hidden, for: .navigationBar)
            .onAppear {
                guard !hasLoaded else { return }
                hasLoaded = true
                Task { await viewModel.load() }
            }
        }
    }
}

private struct BrandSection: View {
    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            HStack(spacing: ClavisTheme.mediumSpacing) {
                ClavisBrandMark()
                    .frame(width: 34, height: 34)

                VStack(alignment: .leading, spacing: 4) {
                    Text("CLAVIS")
                        .font(ClavisTypography.h2)
                        .foregroundColor(.textPrimary)
                        .kerning(1.4)

                    Text("Minimal portfolio intelligence")
                        .font(ClavisTypography.bodySmall)
                        .foregroundColor(.textSecondary)
                }
            }

            Text("A clean shell for monitoring risk, reviewing change, and wiring in portfolio connections as the product grows.")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

struct AccountSection: View {
    let userEmail: String
    let onSignOut: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Account")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            SettingsLabelRow(label: "Email", value: userEmail)

            Button("Sign Out", role: .destructive, action: onSignOut)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.top, ClavisTheme.smallSpacing)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

struct SettingsLabelRow: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label.uppercased())
                .font(ClavisTypography.label)
                .kerning(0.88)
                .foregroundColor(.textTertiary)
            Text(value)
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
        }
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
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Digest")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text("DAILY DIGEST TIME")
                    .font(ClavisTypography.label)
                    .kerning(0.88)
                    .foregroundColor(.textTertiary)

                HStack {
                    DatePicker("", selection: $digestTime, displayedComponents: .hourAndMinute)
                        .labelsHidden()
                        .onChange(of: digestTime) { _, _ in onDigestTimeChange() }
                    Spacer()
                }
            }

            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text("SUMMARY LENGTH")
                    .font(ClavisTypography.label)
                    .kerning(0.88)
                    .foregroundColor(.textTertiary)

                Picker("Summary Length", selection: $summaryLength) {
                    ForEach(SummaryLength.allCases, id: \.self) { length in
                        Text(length.rawValue).tag(length)
                    }
                }
                .pickerStyle(.segmented)
                .onChange(of: summaryLength) { _, _ in onSummaryLengthChange() }
            }

            Toggle("Weekday Only", isOn: $weekdayOnly)
                .foregroundColor(.textPrimary)
                .onChange(of: weekdayOnly) { _, _ in onWeekdayOnlyChange() }

            Text("Changes are saved automatically.")
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
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
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("Alerts")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            SettingsToggleRow(label: "Grade Changes", isOn: $alertsGradeChanges, onChange: onAlertSettingsChange)
            SettingsToggleRow(label: "Major Events", isOn: $alertsMajorEvents, onChange: onAlertSettingsChange)
            SettingsToggleRow(label: "Portfolio Risk Changes", isOn: $alertsPortfolioRisk, onChange: onAlertSettingsChange)

            Divider()
                .background(Color.border)

            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Toggle("Quiet Hours", isOn: $quietHoursEnabled)
                    .foregroundColor(.textPrimary)
                    .onChange(of: quietHoursEnabled) { _, _ in onAlertSettingsChange() }

                if quietHoursEnabled {
                    VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                        QuietHoursTimeRow(label: "From", time: $quietHoursStart, onChange: onAlertSettingsChange)
                        QuietHoursTimeRow(label: "To", time: $quietHoursEnd, onChange: onAlertSettingsChange)
                    }
                    .padding(.top, ClavisTheme.smallSpacing)
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

struct SettingsToggleRow: View {
    let label: String
    @Binding var isOn: Bool
    let onChange: () -> Void

    var body: some View {
        Toggle(label, isOn: $isOn)
            .foregroundColor(.textPrimary)
            .onChange(of: isOn) { _, _ in onChange() }
    }
}

struct QuietHoursTimeRow: View {
    let label: String
    @Binding var time: Date
    let onChange: () -> Void

    var body: some View {
        HStack {
            Text(label)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)
                .frame(width: 40, alignment: .leading)

            DatePicker("", selection: $time, displayedComponents: .hourAndMinute)
                .labelsHidden()
                .onChange(of: time) { _, _ in onChange() }

            Spacer()
        }
        .padding(.vertical, ClavisTheme.smallSpacing)
        .clavisSecondaryCardStyle(fill: .surfaceElevated)
    }
}

struct AboutSection: View {
    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
            Text("About")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)

            SettingsLabelRow(label: "Version", value: "1.0.0")

            Divider()
                .background(Color.border)

            NavigationLink(destination: ScoreExplanationView()) {
                SettingsNavigationRow(title: "Score Explanation")
            }

            NavigationLink(destination: MethodologyView()) {
                SettingsNavigationRow(title: "Methodology Overview")
            }

            Divider()
                .background(Color.border)

            SettingsLinkRow(title: "Privacy Policy", urlString: "https://clavis.app/privacy")
            SettingsLinkRow(title: "Terms of Service", urlString: "https://clavis.app/terms")
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

struct SettingsNavigationRow: View {
    let title: String

    var body: some View {
        HStack {
            Text(title)
                .font(ClavisTypography.body)
                .foregroundColor(.textPrimary)
            Spacer()
            Image(systemName: "chevron.right")
                .font(.system(size: 12, weight: .semibold))
                .foregroundColor(.textTertiary)
        }
        .padding(.vertical, ClavisTheme.smallSpacing)
    }
}

struct SettingsLinkRow: View {
    let title: String
    let urlString: String

    var body: some View {
        Link(destination: URL(string: urlString)!) {
            HStack {
                Text(title)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textPrimary)
                Spacer()
                Image(systemName: "arrow.up.right")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.textTertiary)
            }
            .padding(.vertical, ClavisTheme.smallSpacing)
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
                    ScoreBandRow(grade: "A", range: "75–100", description: "Safe — minimum risk exposure", color: .riskA)
                    ScoreBandRow(grade: "B", range: "55–74", description: "Stable — low risk", color: .riskB)
                    ScoreBandRow(grade: "C", range: "35–54", description: "Watch — moderate risk", color: .riskC)
                    ScoreBandRow(grade: "D", range: "15–34", description: "Risky — elevated risk", color: .riskD)
                    ScoreBandRow(grade: "F", range: "0–14", description: "Critical — high risk", color: .riskF)
                }
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

                    Text("Clavis evaluates positions across multiple risk dimensions including market structure, macro sensitivity, sentiment, and catalyst quality.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }

                VStack(alignment: .leading, spacing: ClavisTheme.mediumSpacing) {
                    MethodologyStepRow(number: "01", title: "Data Collection", description: "Real-time price, news, and market structure signals are gathered for each position.")
                    MethodologyStepRow(number: "02", title: "Relevance Filtering", description: "Market noise is filtered out so only position-relevant stories move forward.")
                    MethodologyStepRow(number: "03", title: "Risk Analysis", description: "Each position is scored across five dimensions: news sentiment, macro exposure, position sizing, volatility trend, and market integrity.")
                    MethodologyStepRow(number: "04", title: "Grade Assignment", description: "Composite scores are mapped to letter grades with fixed boundaries.")
                }
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
