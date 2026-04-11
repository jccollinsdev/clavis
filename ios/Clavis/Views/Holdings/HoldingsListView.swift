import SwiftUI

struct HoldingsListView: View {
    @StateObject private var viewModel = HoldingsViewModel()

    private var sortedHoldings: [Position] {
        viewModel.holdings.sorted { ($0.totalScore ?? 50) < ($1.totalScore ?? 50) }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                Color.backgroundPrimary.ignoresSafeArea()

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
                                .listRowInsets(EdgeInsets(top: 0, leading: 16, bottom: 0, trailing: 16))
                        }

                        // Column headers
                        PositionTableHeader()
                            .listRowSeparator(.hidden)
                            .listRowBackground(Color.clear)
                            .listRowInsets(EdgeInsets(top: 0, leading: 0, bottom: 0, trailing: 0))

                        ForEach(sortedHoldings) { position in
                            holdingRow(for: position)
                        }
                    }
                    .listStyle(.plain)
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
            PositionTableRow(position: position)
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
        .listRowSeparator(.automatic)
        .listRowSeparatorTint(Color.border)
        .listRowBackground(Color.backgroundPrimary)
        .listRowInsets(EdgeInsets(top: 0, leading: 0, bottom: 0, trailing: 0))
    }
}

// MARK: - Position Table Header

struct PositionTableHeader: View {
    var body: some View {
        HStack(spacing: 12) {
            Text("TICKER")
                .font(ClavisTypography.label)
                .kerning(0.88)
                .foregroundColor(.textSecondary)
                .frame(minWidth: 44, alignment: .leading)

            Spacer()

            Text("RISK")
                .font(ClavisTypography.label)
                .kerning(0.88)
                .foregroundColor(.textSecondary)
                .frame(width: 66, alignment: .trailing)
        }
        .padding(.vertical, 6)
        .padding(.horizontal, 16)
    }
}

// MARK: - Position Table Row

struct PositionTableRow: View {
    let position: Position

    var body: some View {
        HStack(spacing: 12) {
            Text(position.ticker)
                .font(ClavisTypography.rowTicker)
                .foregroundColor(.textPrimary)
                .frame(minWidth: 44, alignment: .leading)
                .lineLimit(1)

            RiskBar(
                score: position.totalScore ?? 50,
                grade: position.riskGrade ?? "C"
            )
            .frame(maxWidth: .infinity)

            HStack(spacing: 6) {
                Text("\(Int((position.totalScore ?? 0).rounded()))")
                    .font(ClavisTypography.rowScore)
                    .foregroundColor(ClavisGradeStyle.riskColor(for: position.riskGrade))
                    .frame(width: 28, alignment: .trailing)
                    .monospacedDigit()

                GradeTag(grade: position.riskGrade ?? "C", compact: true)
            }
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 16)
        .contentShape(Rectangle())   // full row is tap target — no chevron
    }
}

// MARK: - Holdings Empty State

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
                    .tint(Color.informational)
            }
            .padding(ClavisTheme.cardPadding)
            .clavisCardStyle()
        }
        .padding(.horizontal, ClavisTheme.screenPadding)
        .padding(.vertical, ClavisTheme.largeSpacing)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }
}

// MARK: - Backward compat: keep HoldingRow as alias
typealias HoldingRow = PositionTableRow

// MARK: - Add Position Sheet

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

// MARK: - Add Position Progress View

struct AddPositionProgressView: View {
    @ObservedObject var viewModel: HoldingsViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(spacing: 32) {
                Spacer()

                VStack(spacing: 20) {
                    // Status icon
                    ZStack {
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color.surface)
                            .frame(width: 80, height: 80)
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.border, lineWidth: 1))

                        Image(systemName: viewModel.progressValue >= 1.0 ? "checkmark" : "chart.line.uptrend.xyaxis")
                            .font(.system(size: 28, weight: .medium))
                            .foregroundColor(viewModel.progressValue >= 1.0 ? .riskA : .textSecondary)
                            .animation(.linear(duration: 0.3), value: viewModel.progressValue)
                    }

                    VStack(spacing: 6) {
                        Text(primaryProgressMessage)
                            .font(ClavisTypography.h2)
                            .foregroundColor(.textPrimary)
                            .multilineTextAlignment(.center)

                        Text(progressDescription)
                            .font(ClavisTypography.body)
                            .foregroundColor(.textSecondary)
                            .multilineTextAlignment(.center)
                    }

                    // Progress bar — flat, no capsule
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            Rectangle()
                                .fill(Color.border)
                                .frame(height: 4)
                            Rectangle()
                                .fill(ClavisGradeStyle.riskColor(for: progressGrade))
                                .frame(width: geo.size.width * CGFloat(viewModel.progressValue), height: 4)
                                .animation(.spring(response: 0.5, dampingFraction: 0.82), value: viewModel.progressValue)
                        }
                    }
                    .frame(height: 4)

                    Text(progressStageText)
                        .font(ClavisTypography.label)
                        .kerning(0.88)
                        .foregroundColor(.textSecondary)
                        .multilineTextAlignment(.center)
                }
                .padding(.horizontal, 24)
                .padding(.vertical, 28)
                .background(Color.surface)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.border, lineWidth: 1))
                .clipShape(RoundedRectangle(cornerRadius: 8))

                Spacer()
            }
            .padding(24)
            .background(Color.backgroundPrimary.ignoresSafeArea())
            .navigationTitle(viewModel.pendingTicker ?? "New Position")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }

    private var primaryProgressMessage: String {
        viewModel.progressValue >= 1.0 ? "Analysis complete" : viewModel.progressMessage
    }

    private var progressDescription: String {
        if let pendingTicker = viewModel.pendingTicker {
            return "\(pendingTicker) was added. Clavix is now analyzing this holding."
        }
        return "Preparing your new holding."
    }

    private var progressGrade: String {
        if viewModel.progressValue >= 1.0 { return "A" }
        if viewModel.progressValue >= 0.6 { return "B" }
        if viewModel.progressValue >= 0.3 { return "C" }
        return "D"
    }

    private var progressStageText: String {
        if viewModel.progressValue >= 1.0 { return "POSITION READY" }
        switch viewModel.progressMessage {
        case let m where m.contains("Adding"):      return "CREATING POSITION"
        case let m where m.contains("Queueing"):    return "SCHEDULING ANALYSIS"
        case let m where m.contains("Fetching"):    return "COLLECTING CONTEXT"
        case let m where m.contains("Classifying"): return "MATCHING HEADLINES"
        case let m where m.contains("Analyzing"):   return "SCORING POSITION"
        case let m where m.contains("Building"):    return "WRITING REPORT"
        default:                                     return "RUNNING ANALYSIS"
        }
    }
}

// Keep AnimatedProgressBar defined for any remaining references
struct AnimatedProgressBar: View {
    let progress: Double
    let shimmerPhase: CGFloat

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Rectangle().fill(Color.border).frame(height: 4)
                Rectangle()
                    .fill(Color.riskB)
                    .frame(width: geo.size.width * CGFloat(min(max(progress, 0), 1)), height: 4)
                    .animation(.spring(response: 0.5, dampingFraction: 0.82), value: progress)
            }
        }
        .frame(height: 4)
    }
}
