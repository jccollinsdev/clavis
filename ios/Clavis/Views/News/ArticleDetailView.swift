import SwiftUI

struct ArticleDetailView: View {
    @Environment(\.dismiss) private var dismiss
    let articleId: String
    let preloadedArticle: NewsStory?

    @StateObject private var viewModel: ArticleDetailViewModel

    init(articleId: String, preloadedArticle: NewsStory? = nil) {
        self.articleId = articleId
        self.preloadedArticle = preloadedArticle
        _viewModel = StateObject(wrappedValue: ArticleDetailViewModel(articleId: articleId, preloadedArticle: preloadedArticle))
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                ArticleTopBar(
                    title: viewModel.article?.source ?? "Article",
                    onBack: { dismiss() }
                )

                if let errorMessage = viewModel.errorMessage {
                    DashboardErrorCard(message: errorMessage)
                }

                if viewModel.isLoading && viewModel.article == nil {
                    ClavisLoadingCard(title: "Loading article", subtitle: "Pulling the saved article detail.")
                }

                if let article = viewModel.article {
                    ArticleHeaderCard(article: article)
                    ArticleBodyCard(article: article)

                    if let impact = article.impact, !impact.isEmpty {
                        ArticleImpactCard(article: article, impact: impact)
                    }

                    if !viewModel.relatedAlerts.isEmpty {
                        RelatedAlertsCard(alerts: viewModel.relatedAlerts)
                    }

                    if let ticker = article.ticker, !ticker.isEmpty {
                        NavigationLink(destination: TickerDetailView(ticker: ticker)) {
                            Text("View \(ticker) detail →")
                                .font(ClavisTypography.bodyEmphasis)
                                .frame(maxWidth: .infinity)
                                .padding(ClavisTheme.cardPadding)
                                .clavisCardStyle(fill: .surfaceElevated)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.vertical, ClavisTheme.largeSpacing)
            .padding(.bottom, ClavisTheme.extraLargeSpacing)
        }
        .background(ClavisAtmosphereBackground())
        .toolbar(.hidden, for: .navigationBar)
        .task {
            await viewModel.load()
        }
        .refreshable {
            await viewModel.load()
        }
    }
}

private struct ArticleTopBar: View {
    let title: String
    let onBack: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Button(action: onBack) {
                Text("‹ Back")
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.informational)
            }
            .buttonStyle(.plain)

            Text(title)
                .font(.system(size: 17, weight: .semibold))
                .foregroundColor(.textPrimary)

            Spacer()
        }
    }
}

private struct ArticleHeaderCard: View {
    let article: NewsStory

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center) {
                GradeTag(grade: article.grade ?? article.currentGrade ?? "C", compact: true)
                Text(article.ticker ?? article.category.title.uppercased())
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.textSecondary)
                Spacer()
                Text(article.source ?? "")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.textSecondary)
            }

            Text(article.title)
                .font(ClavisTypography.h2)
                .foregroundColor(.textPrimary)
                .lineLimit(nil)

            Text(article.displayTimestamp)
                .font(ClavisTypography.footnote)
                .foregroundColor(.textTertiary)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

private struct ArticleBodyCard: View {
    let article: NewsStory

    private var paragraphs: [String] {
        let raw = article.articleBody
        let cleaned = raw
            .components(separatedBy: "\n\n")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }

        guard let first = cleaned.first else { return cleaned }
        let normalizedTitle = article.title.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let normalizedFirst = first.lowercased()
        if !normalizedTitle.isEmpty,
           (normalizedFirst == normalizedTitle || normalizedFirst.hasPrefix("\(normalizedTitle) ")) {
            return Array(cleaned.dropFirst())
        }

        return cleaned
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach(Array(paragraphs.enumerated()), id: \.offset) { _, paragraph in
                Text(paragraph)
                    .font(ClavisTypography.body)
                    .foregroundColor(.textSecondary)
                    .lineSpacing(4)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

private struct ArticleImpactCard: View {
    let article: NewsStory
    let impact: String

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("FOR YOUR POSITION")
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)

            HStack(alignment: .top, spacing: 12) {
                GradeTag(grade: article.previousGrade ?? article.currentGrade ?? article.grade ?? "C", large: true)

                VStack(alignment: .leading, spacing: 8) {
                    Text(article.factored ? "Factored into score" : "Not yet scored")
                        .font(ClavisTypography.bodyEmphasis)
                        .foregroundColor(.textPrimary)

                    Text(impact)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)

                }
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}

private struct RelatedAlertsCard: View {
    let alerts: [Alert]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("RELATED ALERTS")
                .font(ClavisTypography.label)
                .foregroundColor(.textSecondary)

            ForEach(alerts.prefix(3)) { alert in
                VStack(alignment: .leading, spacing: 4) {
                    Text(alert.type.displayName)
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.textPrimary)
                    Text(alert.message)
                        .font(ClavisTypography.body)
                        .foregroundColor(.textSecondary)
                }
                .padding(ClavisTheme.cardPadding)
                .clavisSecondaryCardStyle(fill: .surfaceElevated)
            }
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}
