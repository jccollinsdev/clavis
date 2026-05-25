import SwiftUI
import UIKit

struct ArticleDetailSheet: View {
    let article: MethodologyArticle
    let ticker: String

    @Environment(\.dismiss) private var dismiss
    @State private var showWhyThisScore = false

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    headlineBlock
                    metadataBlock
                    sentimentBlock
                    impactTagBlock
                    tldrSection
                    whatItMeansSection
                    keyImplicationsSection
                    whyThisScoreSection
                    readOriginalButton
                }
                .padding(.horizontal, ClavisTheme.screenPadding)
                .padding(.vertical, ClavisTheme.sectionSpacing)
            }
            .background(Color.clavixPage.ignoresSafeArea())
            .navigationTitle("Article Detail")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { dismiss() }
                        .foregroundColor(.informational)
                }
            }
        }
    }

    private var headlineBlock: some View {
        Text(article.title ?? "")
            .font(ClavisTypography.inter(18, weight: .semibold))
            .foregroundColor(.clavixInk)
            .fixedSize(horizontal: false, vertical: true)
    }

    private var metadataBlock: some View {
        HStack(spacing: 8) {
            if let source = article.source {
                Text(source)
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.clavixInk3)
            }
            if let date = article.publishedAt {
                Text("·")
                    .foregroundColor(.clavixInk4)
                Text(date.prefix(10))
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.clavixInk4)
            }
            if let tier = article.sourceTier {
                tierPill(tier)
            }
        }
    }

    private var sentimentBlock: some View {
        HStack(spacing: 12) {
            if let score = article.sentimentScore {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Sentiment")
                        .font(ClavisTypography.label)
                        .foregroundColor(.clavixInk3)
                    Text("\(Int(score.rounded()))")
                        .font(.system(size: 36, weight: .bold, design: .monospaced))
                        .foregroundColor(sentimentColor(score))
                }
            }

            Spacer()

            if let rw = article.recencyWeight {
                VStack(alignment: .trailing, spacing: 4) {
                    Text("Recency")
                        .font(ClavisTypography.label)
                        .foregroundColor(.clavixInk3)
                    HStack(spacing: 4) {
                        Text("\(Int(rw.rounded()))x")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(.gradeCBBB)
                    }
                }
            }
        }
        .padding()
        .background(Color.clavixPaper2)
        .cornerRadius(ClavisTheme.innerCornerRadius)
    }

    private var impactTagBlock: some View {
        HStack {
            if let tag = article.impactTag {
                Text(tag.replacingOccurrences(of: "-", with: " ").capitalized)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.gradeCBB)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Color.gradeCBB.opacity(0.12))
                    .cornerRadius(4)
            }
        }
    }

    private var tldrSection: some View {
        sectionBlock(title: "TLDR") {
            Text(article.tldr ?? "Not available.")
                .font(ClavisTypography.body)
                .foregroundColor(.clavixInk)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var whatItMeansSection: some View {
        sectionBlock(title: "What It Means for \(ticker)") {
            Text(article.whatItMeans ?? "Not available.")
                .font(ClavisTypography.body)
                .foregroundColor(.clavixInk)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var keyImplicationsSection: some View {
        sectionBlock(title: "Key Implications") {
            VStack(alignment: .leading, spacing: 6) {
                if let implications = article.keyImplications, !implications.isEmpty {
                    ForEach(implications, id: \.self) { implication in
                        HStack(alignment: .top, spacing: 8) {
                            Text("•")
                                .font(ClavisTypography.body)
                                .foregroundColor(.clavixInk4)
                            Text(implication)
                                .font(ClavisTypography.body)
                                .foregroundColor(.clavixInk3)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                } else {
                    Text("Not available.")
                        .font(ClavisTypography.body)
                        .foregroundColor(.clavixInk3)
                }
            }
        }
    }

    private var whyThisScoreSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Button(action: { withAnimation { showWhyThisScore.toggle() } }) {
                HStack {
                    Text("Why this score?")
                        .font(ClavisTypography.label)
                        .foregroundColor(.clavixInk3)
                    Spacer()
                    Image(systemName: showWhyThisScore ? "chevron.up" : "chevron.down")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(.clavixInk4)
                }
            }
            .buttonStyle(.plain)

            if showWhyThisScore {
                Text(article.sentimentReason ?? "Score reasoning not available.")
                    .font(ClavisTypography.footnote)
                    .foregroundColor(.clavixInk3)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.top, 4)
            }
        }
    }

    private var readOriginalButton: some View {
        VStack(spacing: 0) {
            Divider().background(Color.border)
                .padding(.vertical, 8)

            Button {
                if let sourceUrl = article.sourceUrl,
                   let url = URL(string: sourceUrl) {
                    UIApplication.shared.open(url)
                }
            } label: {
                HStack {
                    Image(systemName: "safari")
                        .font(.system(size: 14))
                    Text("Read original article")
                        .font(ClavisTypography.bodyEmphasis)
                    Spacer()
                    Image(systemName: "arrow.up.right")
                        .font(.system(size: 12))
                }
                .foregroundColor(.informational)
                .padding(.vertical, 10)
            }
            .buttonStyle(.plain)
        }
    }

    private func sectionBlock<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(ClavisTypography.label)
                .foregroundColor(.clavixInk3)
                .textCase(.uppercase)
            content()
        }
        .padding()
        .background(Color.clavixPaper2)
        .cornerRadius(ClavisTheme.innerCornerRadius)
    }

    private func sentimentColor(_ score: Double) -> Color {
        if score >= 70 { return .gradeCAA }
        if score >= 50 { return .gradeCBB }
        return .gradeCF
    }

    private func tierPill(_ tier: Int) -> some View {
        Text("T\(tier)")
            .font(.system(size: 9, weight: .bold))
            .foregroundColor(.gradeCAA)
            .padding(.horizontal, 4)
            .padding(.vertical, 1)
            .background(Color.gradeCAA.opacity(0.12))
            .cornerRadius(3)
    }
}
