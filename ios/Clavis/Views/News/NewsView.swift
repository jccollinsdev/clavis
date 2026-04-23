import SwiftUI

struct NewsView: View {
    @Environment(\.dismiss) private var dismiss
    @StateObject private var viewModel = NewsViewModel()

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: ClavisTheme.sectionSpacing) {
                NewsTopBar(
                    title: "News",
                    subtitle: updatedSubtitle,
                    onBack: { dismiss() }
                )

                if let errorMessage = viewModel.errorMessage {
                    DashboardErrorCard(message: errorMessage)
                }

                filterBar

                if viewModel.isLoading && viewModel.stories.isEmpty {
                    ClavisLoadingCard(title: "Loading news", subtitle: "Fetching portfolio, watchlist, and market stories.")
                } else if let hero = heroStory {
                    NavigationLink(destination: ArticleDetailView(articleId: hero.id, preloadedArticle: hero)) {
                        NewsHeroCard(story: hero)
                    }
                    .buttonStyle(.plain)

                    if !storyRows.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("More stories")
                                .font(ClavisTypography.label)
                                .foregroundColor(.textSecondary)

                            VStack(spacing: 0) {
                                ForEach(storyRows) { story in
                                    NavigationLink(destination: ArticleDetailView(articleId: story.id, preloadedArticle: story)) {
                                        NewsStoryCard(story: story)
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                            .padding(.horizontal, 14)
                            .padding(.vertical, 4)
                            .clavisCardStyle(fill: .surface)
                        }
                    }
                } else {
                    NewsEmptyStateCard()
                }
            }
            .padding(.horizontal, ClavisTheme.screenPadding)
            .padding(.vertical, ClavisTheme.largeSpacing)
            .padding(.bottom, ClavisTheme.extraLargeSpacing)
        }
        .background(ClavisAtmosphereBackground())
        .toolbar(.hidden, for: .navigationBar)
        .refreshable {
            await viewModel.refresh()
        }
        .task {
            await viewModel.load()
        }
    }

    private var heroStory: NewsStory? {
        viewModel.heroStory ?? viewModel.stories.first
    }

    private var storyRows: [NewsStory] {
        guard let heroStory else { return [] }
        return viewModel.stories.filter { $0.id != heroStory.id }
    }

    private var filterBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 7) {
                ForEach(NewsCategory.allCases, id: \.rawValue) { category in
                    Button {
                        viewModel.selectedCategory = category
                    } label: {
                    Text(chipLabel(for: category))
                            .font(.system(size: 15, weight: viewModel.selectedCategory == category ? .semibold : .medium))
                            .foregroundColor(viewModel.selectedCategory == category ? .textPrimary : .textSecondary)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(viewModel.selectedCategory == category ? Color.surfaceElevated : Color.surface)
                            .overlay(
                                RoundedRectangle(cornerRadius: 999, style: .continuous)
                                    .stroke(viewModel.selectedCategory == category ? Color.textPrimary : Color.border, lineWidth: 1)
                            )
                            .clipShape(Capsule())
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func chipLabel(for category: NewsCategory) -> String {
        guard let counts = viewModel.counts else { return category.title }

        switch category {
        case .all:
            let total = counts.portfolio + counts.watchlist + counts.market + counts.major
            return "All · \(total)"
        case .portfolio:
            return "Portfolio · \(counts.portfolio)"
        case .watchlist:
            return "Watchlist · \(counts.watchlist)"
        case .market:
            return "Market · \(counts.market)"
        case .major:
            return "Major · \(counts.major)"
        }
    }

    private var updatedSubtitle: String {
        if let updatedAt = viewModel.updatedAt {
            return "Updated \(updatedAt.formatted(date: .omitted, time: .shortened))"
        }
        return "Updated just now"
    }
}

private struct NewsTopBar: View {
    let title: String
    let subtitle: String
    let onBack: () -> Void

    var body: some View {
        HStack(alignment: .bottom, spacing: 12) {
            Button(action: onBack) {
                Text("‹ Back")
                    .font(ClavisTypography.footnoteEmphasis)
                    .foregroundColor(.informational)
            }
            .buttonStyle(.plain)

            VStack(alignment: .leading, spacing: 3) {
                Text(subtitle)
                    .font(ClavisTypography.label)
                    .foregroundColor(.textSecondary)
                Text(title)
                    .font(.system(size: 26, weight: .bold))
                    .foregroundColor(.textPrimary)
            }

            Spacer()
        }
    }
}

private struct NewsHeroCard: View {
    let story: NewsStory

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .fill(Color.surfaceElevated)
                .frame(height: 140)
                .overlay(
                    VStack(alignment: .leading, spacing: 8) {
                        GradeTag(grade: story.grade ?? story.currentGrade ?? "C", compact: true)
                        Spacer()
                    }
                    .padding(14)
                )

            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .center, spacing: 8) {
                    GradeTag(grade: story.grade ?? story.currentGrade ?? "C", compact: true)
                    Text(story.ticker ?? story.category.title.uppercased())
                        .font(.system(size: 15, weight: .semibold, design: .monospaced))
                        .foregroundColor(.textPrimary)
                    Text("· \(story.source ?? "") · \(story.displayTimestamp)")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                }

                Text(story.title)
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundColor(.textPrimary)
                    .multilineTextAlignment(.leading)

                Text(story.summary ?? story.impact ?? "")
                    .font(ClavisTypography.bodySmall)
                    .foregroundColor(.textSecondary)
                    .lineLimit(3)

                HStack {
                    Text(relevanceText)
                        .font(.system(size: 15, weight: .medium, design: .monospaced))
                        .foregroundColor(.textPrimary)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(relevanceBackground)
                        .overlay(
                            RoundedRectangle(cornerRadius: 4, style: .continuous)
                                .stroke(Color.border, lineWidth: 1)
                        )
                        .clipShape(RoundedRectangle(cornerRadius: 4, style: .continuous))

                    Spacer()

                    Text("Read article →")
                        .font(ClavisTypography.footnoteEmphasis)
                        .foregroundColor(.informational)
                }
            }
            .padding(14)
        }
        .clavisCardStyle(fill: .surface)
    }

    private var relevanceText: String {
        "\((story.relevance ?? "Medium")) relevance"
    }

    private var relevanceBackground: Color {
        switch (story.relevance ?? "medium").lowercased() {
        case "high": return .dangerSurface
        case "low": return .surface
        default: return .surfaceElevated
        }
    }
}

private struct NewsStoryCard: View {
    let story: NewsStory

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            RoundedRectangle(cornerRadius: 6, style: .continuous)
                .fill(Color.surfaceElevated)
                .frame(width: 60, height: 60)
                .overlay(
                    GradeTag(grade: story.grade ?? story.currentGrade ?? "C", compact: true)
                )

            VStack(alignment: .leading, spacing: 4) {
                HStack(alignment: .center, spacing: 6) {
                    Text(story.ticker ?? story.category.title.uppercased())
                        .font(.system(size: 15, weight: .semibold, design: .monospaced))
                        .foregroundColor(.textPrimary)
                    Text("· \(story.source ?? "")")
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)
                }

                Text(story.title)
                    .font(ClavisTypography.bodyEmphasis)
                    .foregroundColor(.textPrimary)
                    .multilineTextAlignment(.leading)
                    .lineLimit(2)

                HStack {
                    Text(story.displayTimestamp)
                        .font(ClavisTypography.footnote)
                        .foregroundColor(.textSecondary)

                    Spacer()

                    Text(story.relevance ?? story.category.title)
                        .font(.system(size: 15, weight: .medium, design: .monospaced))
                        .foregroundColor((story.relevance ?? "").lowercased() == "high" ? .riskD : .textSecondary)
                }
            }
        }
        .padding(.vertical, 12)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(Color.border)
                .frame(height: 1)
        }
    }
}

private struct NewsEmptyStateCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("No stories right now")
                .font(ClavisTypography.cardTitle)
                .foregroundColor(.textPrimary)
            Text("Try adding holdings to see relevant portfolio and watchlist coverage.")
                .font(ClavisTypography.body)
                .foregroundColor(.textSecondary)
        }
        .padding(ClavisTheme.cardPadding)
        .clavisCardStyle(fill: .surface)
    }
}
