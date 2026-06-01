import SwiftUI
import UIKit

struct ArticleDetailSheet: View {
    let article: MethodologyArticle
    let ticker: String
    var portfolioContext: String? = nil

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Article title — main heading
                Text(article.title?.sanitizedDisplayText ?? "Untitled article")
                    .font(ClavisTypography.clavixSerif(26, weight: .medium))
                    .foregroundColor(.clavixInk)
                    .fixedSize(horizontal: false, vertical: true)

                // Impact pill + source tier + timestamp
                HStack(spacing: 8) {
                    impactPill
                    if let tier = article.sourceTier {
                        tierBadge(tier)
                    }
                    Text("·")
                        .font(ClavisTypography.clavixMono(10, weight: .regular))
                        .foregroundColor(.clavixInk4)
                    Text(relativeTimestamp)
                        .font(ClavisTypography.clavixMono(10, weight: .regular))
                        .foregroundColor(.clavixInk3)
                    Spacer()
                }

                Rectangle()
                    .fill(Color.clavixRule)
                    .frame(height: 1)

                VStack(alignment: .leading, spacing: 6) {
                    ClavixEyebrow("Brief")
                    Text(briefText)
                        .font(ClavisTypography.clavixSerif(16, weight: .regular))
                        .foregroundColor(.clavixInk2)
                        .fixedSize(horizontal: false, vertical: true)
                }

                if let portfolioContextText {
                    ClavixCard(fill: .clavixAccentSoft) {
                        VStack(alignment: .leading, spacing: 8) {
                            ClavixEyebrow("Portfolio context")
                            Text(portfolioContextText)
                                .font(ClavisTypography.clavixSerif(15, weight: .regular))
                                .foregroundColor(.clavixAccentInk)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }

                VStack(alignment: .leading, spacing: 6) {
                    ClavixEyebrow("Risk signal")
                    ClavixCard {
                        HStack(alignment: .top, spacing: 12) {
                            Text(sentimentValueText)
                                .font(ClavisTypography.clavixMono(26, weight: .semibold))
                                .foregroundColor(sentimentColor)

                            Text(riskSignalText)
                                .font(ClavisTypography.clavixCaption)
                                .foregroundColor(.clavixInk2)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }

                if let implications = article.keyImplications, !implications.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        ClavixEyebrow("Key implications")
                        ClavixCard {
                            VStack(alignment: .leading, spacing: 10) {
                                ForEach(Array(implications.prefix(4).enumerated()), id: \.offset) { _, implication in
                                    HStack(alignment: .top, spacing: 10) {
                                        Circle()
                                            .fill(Color.clavixAccent)
                                            .frame(width: 5, height: 5)
                                            .padding(.top, 6)
                                        Text(implication.sanitizedDisplayText)
                                            .font(ClavisTypography.clavixCaption)
                                            .foregroundColor(.clavixInk2)
                                            .fixedSize(horizontal: false, vertical: true)
                                    }
                                }
                            }
                        }
                    }
                }

                if let buttonLabel = readOriginalLabel {
                    Button(action: openSourceURL) {
                        Text(buttonLabel)
                            .font(ClavisTypography.inter(15, weight: .semibold))
                            .foregroundColor(.clavixInk)
                            .frame(maxWidth: .infinity)
                            .frame(height: 48)
                            .background(Color.clear)
                            .overlay(
                                RoundedRectangle(cornerRadius: ClavixLayout.controlRadius, style: .continuous)
                                    .stroke(Color.clavixRule, lineWidth: 1)
                            )
                            .clipShape(RoundedRectangle(cornerRadius: ClavixLayout.controlRadius, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, ClavixLayout.pad)
            .padding(.top, 20)
            .padding(.bottom, ClavixLayout.bottomPad)
        }
        .background(Color.clavixPage.ignoresSafeArea())
        .safeAreaInset(edge: .top, spacing: 0) {
            // Header: "Article brief" title + X dismiss button
            HStack(alignment: .center) {
                Text("Article brief")
                    .font(ClavisTypography.clavixSerif(20, weight: .medium))
                    .foregroundColor(.clavixInk)
                Spacer()
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundColor(.clavixInk)
                        .frame(width: 38, height: 38)
                        .background(Color.clavixPaper2)
                        .clipShape(Circle())
                        .overlay(
                            Circle()
                                .stroke(Color.clavixRule, lineWidth: 1)
                        )
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, ClavixLayout.pad)
            .padding(.vertical, 12)
            .background(Color.clavixPage.ignoresSafeArea(edges: .top))
            .overlay(alignment: .bottom) {
                Rectangle().fill(Color.clavixRule).frame(height: 1)
            }
        }
    }

    // MARK: - Computed content

    private var briefText: String {
        if let tldr = article.tldr?.sanitizedDisplayText, !tldr.isEmpty {
            return tldr
        }
        if let whatItMeans = article.whatItMeans?.sanitizedDisplayText, !whatItMeans.isEmpty {
            return whatItMeans
        }
        return "Brief unavailable for this article."
    }

    private var portfolioContextText: String? {
        if let portfolioContext, !portfolioContext.isEmpty {
            return portfolioContext.sanitizedDisplayText
        }
        if let personalised = article.personalisedStructural?.sanitizedDisplayText, !personalised.isEmpty {
            if let narrative = article.personalisedNarrative?.sanitizedDisplayText, !narrative.isEmpty {
                return "\(personalised) \(narrative)"
            }
            return personalised
        }
        return nil
    }

    private var riskSignalText: String {
        if let sentimentReason = article.sentimentReason?.sanitizedDisplayText, !sentimentReason.isEmpty {
            return sentimentReason
        }
        if let whatItMeans = article.whatItMeans?.sanitizedDisplayText, !whatItMeans.isEmpty {
            return whatItMeans
        }
        return "Risk signal unavailable for this article."
    }

    private var sentimentValueText: String {
        guard let score = article.sentimentScore else { return "—" }
        return "\(Int(score.rounded()))"
    }

    private var sentimentColor: Color {
        guard let score = article.sentimentScore else { return .clavixInk3 }
        if score >= 70 { return .clavixGood }
        if score >= 50 { return .clavixWarn }
        return .clavixBad
    }

    private func tierBadge(_ tier: Int) -> some View {
        Text("T\(tier)")
            .font(ClavisTypography.clavixMono(10, weight: .bold))
            .foregroundColor(.clavixInk3)
            .padding(.horizontal, 5)
            .padding(.vertical, 3)
            .background(Color.clavixPaper2)
            .clipShape(RoundedRectangle(cornerRadius: 3, style: .continuous))
    }

    private var impactPill: some View {
        Text(impactLabel)
            .font(ClavisTypography.clavixMono(10, weight: .bold))
            .foregroundColor(impactInk)
            .padding(.horizontal, 6)
            .padding(.vertical, 4)
            .background(impactFill)
            .clipShape(RoundedRectangle(cornerRadius: 3, style: .continuous))
    }

    private var impactLabel: String {
        guard let impactTag = article.impactTag?.sanitizedDisplayText, !impactTag.isEmpty else {
            return "ARTICLE"
        }
        return impactTag
            .replacingOccurrences(of: "_", with: " ")
            .replacingOccurrences(of: "-", with: " ")
            .uppercased()
    }

    private var impactFill: Color {
        let label = impactLabel
        if label.contains("HIGH") { return .clavixWarnSoft }
        if label.contains("LOW") { return .clavixPaper2 }
        return .clavixAccentSoft
    }

    private var impactInk: Color {
        let label = impactLabel
        if label.contains("HIGH") { return .clavixWarnInk }
        if label.contains("LOW") { return .clavixInk2 }
        return .clavixAccentInk
    }

    private var relativeTimestamp: String {
        guard let publishedAt = article.publishedAt, !publishedAt.isEmpty else { return "—" }
        let date = Self.isoDateParser.date(from: publishedAt)
            ?? Self.isoDateParserNoFraction.date(from: publishedAt)
        guard let date else { return publishedAt.prefix(10).description }
        let interval = Date().timeIntervalSince(date)
        if interval < 60 * 60 * 24 * 3 {
            return Self.relativeFormatter.localizedString(for: date, relativeTo: Date())
        }
        return Self.shortDateFormatter.string(from: date)
    }

    private var readOriginalLabel: String? {
        guard article.sourceUrl != nil else { return nil }
        if let source = article.source?.sanitizedDisplayText, !source.isEmpty {
            return "Read full article at \(source) →"
        }
        return "Read full article →"
    }

    private func openSourceURL() {
        guard let sourceUrl = article.sourceUrl,
              let url = URL(string: sourceUrl) else { return }
        UIApplication.shared.open(url)
    }

    private static let isoDateParser: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    private static let isoDateParserNoFraction: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    private static let relativeFormatter: RelativeDateTimeFormatter = {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter
    }()

    private static let shortDateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMM d"
        return formatter
    }()
}
