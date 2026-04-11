import SwiftUI

struct HoldingsListView: View {
    @StateObject private var viewModel = HoldingsViewModel()

    private var sortedHoldings: [Position] {
        viewModel.holdings.sorted { ($0.totalScore ?? 50) < ($1.totalScore ?? 50) }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                ClavisAtmosphereBackground().ignoresSafeArea()

                if viewModel.isLoading && viewModel.holdings.isEmpty {
                    VStack {
                        ClavisLoadingCard(title: "Loading holdings", subtitle: "Pulling positions and the latest scores.")
                    }
                    .padding()
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
                } else if viewModel.holdings.isEmpty {
                    HoldingsEmptyState(onAddPosition: { viewModel.showAddSheet = true })
                } else {
                    List {
                        if let errorMessage = viewModel.errorMessage {
                            DashboardErrorCard(message: errorMessage)
                                .listRowSeparator(.hidden)
                                .listRowBackground(Color.clear)
                        }

                        ForEach(sortedHoldings) { position in
                            holdingRow(for: position)
                        }
                    }
                    .listStyle(.insetGrouped)
                    .scrollContentBackground(.hidden)
                    .background(Color.clear)
                }
            }
            .navigationTitle("Holdings")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        Task { await viewModel.refreshHoldings() }
                    } label: {
                        if viewModel.isRefreshing {
                            ProgressView()
                        } else {
                            Image(systemName: "arrow.clockwise")
                        }
                    }
                    .disabled(viewModel.isRefreshing)
                }
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        viewModel.showAddSheet = true
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $viewModel.showAddSheet) {
                AddPositionSheet(viewModel: viewModel)
            }
            .fullScreenCover(isPresented: $viewModel.showProgressSheet) {
                AddPositionProgressView(viewModel: viewModel)
            }
            .alert("Error", isPresented: $viewModel.showError) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(viewModel.errorMessage ?? "Unknown error")
            }
            .refreshable {
                await viewModel.refreshHoldings()
            }
            .onAppear {
                viewModel.showError = false
                if viewModel.holdings.isEmpty && !viewModel.isLoading {
                    Task { await viewModel.loadHoldings() }
                }
            }
        }
    }

    @ViewBuilder
    private func holdingRow(for position: Position) -> some View {
        NavigationLink(destination: PositionDetailView(positionId: position.id)) {
            HoldingRow(position: position)
        }
        .buttonStyle(.plain)
        .swipeActions(edge: .trailing, allowsFullSwipe: true) {
            Button(role: .destructive) {
                Task { await viewModel.deleteHolding(position) }
            } label: {
                Label("Delete", systemImage: "trash")
            }
        }
        .contextMenu {
            Button(role: .destructive) {
                Task { await viewModel.deleteHolding(position) }
            } label: {
                Label("Delete Position", systemImage: "trash")
            }
        }
        .listRowSeparator(.hidden)
        .listRowBackground(Color.clear)
    }
}

struct HoldingsEmptyState: View {
    let onAddPosition: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: ClavisTheme.largeSpacing) {
            VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                Text("No holdings yet")
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                Text("Add your first position to start tracking downside risk and portfolio updates.")
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)

                Button("Add Position", action: onAddPosition)
                    .buttonStyle(.borderedProminent)
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle(fill: .surfacePrimary)
        }
        .padding(.horizontal, ClavisTheme.screenPadding)
        .padding(.vertical, ClavisTheme.largeSpacing)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(Color.appBackground)
    }
}

struct HoldingRow: View {
    let position: Position

    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            Text(position.riskGrade ?? "--")
                .font(.system(size: 20, weight: .bold))
                .foregroundColor(.white)
                .frame(width: 44, height: 52)
                .background(ClavisGradeStyle.color(for: position.riskGrade))
                .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))

            VStack(alignment: .leading, spacing: 4) {
                Text(position.ticker)
                    .font(ClavisTypography.cardTitle)
                    .foregroundColor(.textPrimary)
                    .lineLimit(1)

                if let summary = position.summary?.sanitizedDisplayText, !summary.isEmpty {
                    Text(summary)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                        .lineLimit(1)
                }
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 4) {
                Text("\(Int(position.totalScore ?? 0))")
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(.textPrimary)

                if let trend = position.riskTrend {
                    Image(systemName: trend.iconName)
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundColor(trendColor(trend))
                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surfacePrimary)
    }

    private func trendColor(_ trend: RiskTrend) -> Color {
        switch trend {
        case .increasing: return .criticalTone
        case .stable: return .textTertiary
        case .improving: return .successTone
        }
    }
}

struct AddPositionSheet: View {
    @ObservedObject var viewModel: HoldingsViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var ticker = ""
    @State private var shares = ""
    @State private var purchasePrice = ""
    @State private var archetype: Archetype = .growth
    @State private var showError = false
    @State private var errorMessage = ""

    private var isFormValid: Bool {
        !ticker.isEmpty && !shares.isEmpty && Double(shares) != nil && !purchasePrice.isEmpty && Double(purchasePrice) != nil
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Position") {
                    TextField("Ticker (e.g., AAPL)", text: $ticker)
                        .textCase(.uppercase)
                        .autocapitalization(.allCharacters)

                    TextField("Shares", text: $shares)
                        .keyboardType(.decimalPad)

                    TextField("Purchase Price", text: $purchasePrice)
                        .keyboardType(.decimalPad)
                }

                Section("Archetype") {
                    Picker("Archetype", selection: $archetype) {
                        ForEach(Archetype.allCases, id: \.self) { arch in
                            Text(arch.displayName).tag(arch)
                        }
                    }
                    .pickerStyle(.menu)
                }
            }
            .navigationTitle("Add Position")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        Task { await addPosition() }
                    }
                    .disabled(!isFormValid)
                }
            }
            .alert("Error", isPresented: $showError) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(errorMessage)
            }
        }
    }

    private func addPosition() async {
        guard let sharesVal = Double(shares), let priceVal = Double(purchasePrice) else {
            errorMessage = "Invalid number format"
            showError = true
            return
        }

        await viewModel.addHolding(
            ticker: ticker.uppercased(),
            shares: sharesVal,
            purchasePrice: priceVal,
            archetype: archetype
        )

        if viewModel.errorMessage == nil {
            dismiss()
        } else {
            errorMessage = viewModel.errorMessage ?? "Unable to add position."
            showError = true
        }
    }
}

struct AddPositionProgressView: View {
    @ObservedObject var viewModel: HoldingsViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var shimmerPhase: CGFloat = -0.35

    var body: some View {
        NavigationStack {
            VStack(spacing: 28) {
                Spacer()

                VStack(spacing: 18) {
                    ZStack {
                        Circle()
                            .fill(
                                RadialGradient(
                                    colors: [Color.accentColor.opacity(0.28), Color.clear],
                                    center: .center,
                                    startRadius: 12,
                                    endRadius: 58
                                )
                            )
                            .frame(width: 140, height: 140)
                            .blur(radius: 1)

                        Circle()
                            .strokeBorder(Color.white.opacity(0.08), lineWidth: 1)
                            .frame(width: 86, height: 86)

                        Image(systemName: viewModel.progressValue >= 1.0 ? "checkmark.circle.fill" : "chart.line.uptrend.xyaxis")
                            .font(.system(size: 30, weight: .semibold))
                            .foregroundStyle(
                                LinearGradient(
                                    colors: [Color.accentColor, Color.green.opacity(0.9)],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .scaleEffect(viewModel.progressValue >= 1.0 ? 1.05 : 1.0)
                            .animation(.spring(response: 0.45, dampingFraction: 0.75), value: viewModel.progressValue)
                    }

                    VStack(spacing: 6) {
                        Text(primaryProgressMessage)
                            .font(.headline)
                            .multilineTextAlignment(.center)
                            .foregroundColor(.textPrimary)

                        Text(progressDescription)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                    }

                    AnimatedProgressBar(progress: Double(viewModel.progressValue), shimmerPhase: shimmerPhase)
                        .frame(height: 18)

                    Text(progressStageText)
                        .font(.footnote.weight(.medium))
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                }
                .padding(.horizontal, 18)
                .padding(.vertical, 24)
                .frame(maxWidth: .infinity)
                .background(
                    RoundedRectangle(cornerRadius: 28, style: .continuous)
                        .fill(.ultraThinMaterial)
                        .overlay(
                            RoundedRectangle(cornerRadius: 28, style: .continuous)
                                .strokeBorder(Color.white.opacity(0.09), lineWidth: 1)
                        )
                )
                .shadow(color: Color.black.opacity(0.12), radius: 24, x: 0, y: 14)

                Spacer()
            }
            .padding(24)
            .background(
                LinearGradient(
                    colors: [Color.appBackground, Color.appBackground.opacity(0.88), Color.accentColor.opacity(0.08)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()
            )
            .navigationTitle(viewModel.pendingTicker ?? "New Position")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
            .onAppear {
                withAnimation(.linear(duration: 1.6).repeatForever(autoreverses: false)) {
                    shimmerPhase = 1.35
                }
            }
        }
    }

    private var primaryProgressMessage: String {
        if viewModel.progressValue >= 1.0 {
            return "Analysis complete"
        }
        return viewModel.progressMessage
    }

    private var progressDescription: String {
        if let pendingTicker = viewModel.pendingTicker {
            return "\(pendingTicker) was added. Clavis is now analyzing this holding."
        }
        return "Preparing your new holding."
    }

    private var progressStageText: String {
        if viewModel.progressValue >= 1.0 {
            return "Position ready"
        }

        switch viewModel.progressMessage {
        case let message where message.contains("Adding"):
            return "Creating the position"
        case let message where message.contains("Queueing"):
            return "Scheduling analysis"
        case let message where message.contains("Fetching"):
            return "Collecting news and context"
        case let message where message.contains("Classifying"):
            return "Matching headlines to the holding"
        case let message where message.contains("Analyzing"):
            return "Scoring the position"
        case let message where message.contains("Building"):
            return "Writing the position report"
        default:
            return "Working through the analysis pipeline"
        }
    }
}

struct AnimatedProgressBar: View {
    let progress: Double
    let shimmerPhase: CGFloat

    var body: some View {
        GeometryReader { proxy in
            let width = proxy.size.width
            let clampedProgress = min(max(progress, 0.0), 1.0)
            let fillWidth = max(24, width * clampedProgress)

            ZStack(alignment: .leading) {
                Capsule()
                    .fill(Color.white.opacity(0.08))

                Capsule()
                    .fill(
                        LinearGradient(
                            colors: [Color.accentColor.opacity(0.95), Color.cyan.opacity(0.9), Color.green.opacity(0.9)],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .frame(width: fillWidth)
                    .overlay(alignment: .leading) {
                        Capsule()
                            .fill(
                                LinearGradient(
                                    colors: [Color.white.opacity(0.0), Color.white.opacity(0.75), Color.white.opacity(0.0)],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .frame(width: max(36, width * 0.18))
                            .offset(x: shimmerOffset(in: width))
                            .blendMode(.screen)
                    }
                    .shadow(color: Color.accentColor.opacity(0.35), radius: 10, x: 0, y: 4)

                Capsule()
                    .strokeBorder(Color.white.opacity(0.18), lineWidth: 1)
            }
            .clipShape(Capsule())
            .animation(.spring(response: 0.5, dampingFraction: 0.82), value: progress)
        }
    }

    private func shimmerOffset(in width: CGFloat) -> CGFloat {
        let sweepWidth = max(36, width * 0.18)
        return (width + sweepWidth) * shimmerPhase - sweepWidth
    }
}
