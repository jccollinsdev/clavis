import SwiftUI

struct NewsSentimentAuditView: View {
    let ticker: String
    let methodology: MethodologyResponse?
    @State private var selectedArticle: MethodologyArticle?

    private var dimension: MethodologyNewsSentiment? { methodology?.dimensions.newsSentiment }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                if let dimension, (dimension.articleCount7d ?? 0) < 3 {
                    AuditLimitedDataView(message: "Limited Data — fewer than 3 relevant articles were available in the seven-day window.")
                } else {
                    AuditHeaderCard(
                        title: "News Sentiment",
                        ticker: ticker,
                        score: dimension?.score,
                        subtitle: "\(dimension?.articleCount7d ?? 0) articles · volume signal \((dimension?.volumeSignal ?? false) ? "active" : "normal")"
                    )

                    AuditSectionCard(title: "Weighting") {
                        Text("Recency tiers: last 24h = 3x, 24-72h = 2x, 72h-7d = 1x. Source tiers: T1, T2, T3 reflect source quality.")
                            .font(ClavisTypography.body)
                            .foregroundColor(.clavixInk3)
                    }

                    AuditSectionCard(title: "Articles") {
                        ForEach(dimension?.articles ?? []) { article in
                            Button(action: { selectedArticle = article }) {
                                VStack(alignment: .leading, spacing: ClavisTheme.smallSpacing) {
                                    Text(article.title ?? "Untitled article")
                                        .font(ClavisTypography.bodyEmphasis)
                                        .foregroundColor(.clavixInk)
                                        .multilineTextAlignment(.leading)
                                    Text("\(article.source ?? "Unknown") · \(article.publishedAt ?? "Date unavailable")")
                                        .font(ClavisTypography.footnote)
                                        .foregroundColor(.clavixInk3)
                                    Text(article.tldr ?? "TLDR unavailable")
                                        .font(ClavisTypography.footnote)
                                        .foregroundColor(.clavixInk3)
                                    HStack(spacing: ClavisTheme.smallSpacing) {
                                        Text(article.sentimentScore.map { "S \(Int($0.rounded()))" } ?? "S —")
                                        Text(article.sourceTier.map { "T\($0)" } ?? "T—")
                                        Text(article.recencyWeight.map { String(format: "%.1fx", $0) } ?? "1.0x")
                                    }
                                    .font(ClavisTypography.label)
                                    .foregroundColor(.clavixAccent)
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(.vertical, ClavisTheme.smallSpacing)
                            }
                            .buttonStyle(.plain)
                        }
                    }

                    AuditSectionCard(title: "Score Calculation") {
                        // TODO: backend expose source_weight values for article-level news audit math.
                        Text("Weighted average (recency-weighted from available payload): \(weightedAverageText)")
                            .font(ClavisTypography.body)
                            .foregroundColor(.clavixInk3)
                    }
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.vertical, ClavisTheme.sectionSpacing)
        }
        .background(Color.clavixPage.ignoresSafeArea())
        .navigationTitle("News Sentiment")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(item: $selectedArticle) { article in
            ArticleDetailSheet(article: article, ticker: ticker)
        }
    }

    private var weightedAverageText: String {
        let articles = dimension?.articles ?? []
        let weighted = articles.compactMap { article -> Double? in
            guard let score = article.sentimentScore else { return nil }
            return score * (article.recencyWeight ?? 1)
        }.reduce(0, +)
        let weights = articles.compactMap { $0.sentimentScore == nil ? nil : ($0.recencyWeight ?? 1) }.reduce(0, +)
        guard weights > 0 else { return "Unavailable" }
        return String(format: "%.1f", weighted / weights)
    }
}
