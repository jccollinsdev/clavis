import Foundation
import SwiftUI

@MainActor
final class NewsViewModel: ObservableObject {
    @Published private(set) var feed: NewsFeedResponse?
    @Published var selectedCategory: NewsCategory = .all
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let api = APIService.shared

    var heroStory: NewsStory? {
        feed?.heroStory
    }

    var counts: NewsFeedCounts? {
        feed?.counts
    }

    var updatedAt: Date? {
        feed?.updatedAt
    }

    var stories: [NewsStory] {
        guard let feed else { return [] }
        if selectedCategory == .all {
            return feed.stories
        }
        return feed.stories.filter { $0.category == selectedCategory }
    }

    func load() async {
        if feed == nil {
            isLoading = true
        }
        errorMessage = nil

        do {
            feed = try await api.fetchNewsFeed()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func refresh() async {
        await load()
    }
}

@MainActor
final class ArticleDetailViewModel: ObservableObject {
    @Published var article: NewsStory?
    @Published var relatedAlerts: [Alert] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let api = APIService.shared
    private let articleId: String
    private let preloadedArticle: NewsStory?

    init(articleId: String, preloadedArticle: NewsStory? = nil) {
        self.articleId = articleId
        self.preloadedArticle = preloadedArticle
        self.article = preloadedArticle
    }

    func load() async {
        if article == nil {
            isLoading = true
        }
        errorMessage = nil

        do {
            let response = try await api.fetchNewsArticle(id: articleId)
            if let fetched = response.article {
                article = fetched
            } else if article == nil {
                article = preloadedArticle
            }
            relatedAlerts = response.relatedAlerts
        } catch {
            if article == nil {
                errorMessage = error.localizedDescription
            }
        }

        isLoading = false
    }
}
