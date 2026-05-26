import SwiftUI

struct PositionDetailView: View {
    let positionId: String
    @State private var resolvedTicker: String?
    @State private var isLoading = true
    @State private var errorMessage: String?
    @State private var hasLoaded = false

    var body: some View {
        Group {
            if let resolvedTicker {
                TickerDetailView(ticker: resolvedTicker, positionId: positionId)
            } else if isLoading {
                PositionDetailSkeletonView()
            } else if let errorMessage {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Unable to load holding")
                        .font(ClavisTypography.cardTitle)
                        .foregroundColor(.clavixInk)
                    Text(errorMessage)
                        .font(ClavisTypography.body)
                        .foregroundColor(.clavixInk3)
                }
                .padding(ClavisTheme.cardPadding)
            }
        }
        .background(ClavisAtmosphereBackground())
        .task {
            guard !hasLoaded else { return }
            hasLoaded = true
            await resolveTicker()
        }
    }

    private func resolveTicker() async {
        isLoading = true
        errorMessage = nil

        do {
            let detail = try await APIService.shared.fetchPositionDetail(id: positionId)
            resolvedTicker = detail.position.ticker
        } catch {
            errorMessage = ClavisCopy.Errors.positionLoad(error)
        }

        isLoading = false
    }
}

struct PositionDetailSkeletonView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                    .fill(Color.clavixPaper2)
                    .frame(height: 180)

                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                    .fill(Color.clavixPaper2)
                    .frame(height: 200)

                RoundedRectangle(cornerRadius: ClavisTheme.cornerRadius, style: .continuous)
                    .fill(Color.clavixPaper2)
                    .frame(height: 150)
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.vertical, ClavisTheme.largeSpacing)
        }
        .background(ClavisAtmosphereBackground())
    }
}
