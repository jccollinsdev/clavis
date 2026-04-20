import Foundation

struct NewsFeedResponse: Codable {
    let heroStory: NewsStory?
    let stories: [NewsStory]
    let counts: NewsFeedCounts?
    let updatedAt: Date?
    let message: String?

    enum CodingKeys: String, CodingKey {
        case heroStory = "hero_story"
        case stories
        case counts
        case updatedAt = "updated_at"
        case message
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        heroStory = try container.decodeIfPresent(NewsStory.self, forKey: .heroStory)
        stories = (try? container.decode([NewsStory].self, forKey: .stories)) ?? []
        counts = try container.decodeIfPresent(NewsFeedCounts.self, forKey: .counts)
        updatedAt = try container.decodeIfPresent(Date.self, forKey: .updatedAt)
        message = try container.decodeIfPresent(String.self, forKey: .message)
    }
}

struct NewsFeedCounts: Codable {
    let portfolio: Int
    let watchlist: Int
    let market: Int
    let major: Int
}

struct NewsArticleResponse: Codable {
    let article: NewsStory?
    let relatedAlerts: [Alert]
    let message: String?

    enum CodingKeys: String, CodingKey {
        case article
        case relatedAlerts = "related_alerts"
        case message
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        article = try container.decodeIfPresent(NewsStory.self, forKey: .article)
        relatedAlerts = (try? container.decode([Alert].self, forKey: .relatedAlerts)) ?? []
        message = try container.decodeIfPresent(String.self, forKey: .message)
    }
}

struct NewsStory: Identifiable, Codable, Hashable {
    let id: String
    let sourceTable: String
    let sourceId: String
    let ticker: String?
    let tickers: [String]
    let title: String
    let summary: String?
    let body: String?
    let source: String?
    let url: String?
    let publishedAt: Date?
    let category: NewsCategory
    let relevance: String?
    let grade: String?
    let previousGrade: String?
    let currentGrade: String?
    let factored: Bool
    let impact: String?
    let heldShares: Double?
    let positionId: String?
    let analysisRunId: String?
    let imageUrl: String?

    enum CodingKeys: String, CodingKey {
        case id
        case sourceTable = "source_table"
        case sourceId = "source_id"
        case ticker
        case tickers
        case title
        case summary
        case body
        case source
        case url
        case publishedAt = "published_at"
        case category
        case relevance
        case grade
        case previousGrade = "previous_grade"
        case currentGrade = "current_grade"
        case factored
        case impact
        case heldShares = "held_shares"
        case positionId = "position_id"
        case analysisRunId = "analysis_run_id"
        case imageUrl = "image_url"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        sourceTable = try container.decodeIfPresent(String.self, forKey: .sourceTable) ?? "ticker_news"
        sourceId = try container.decodeIfPresent(String.self, forKey: .sourceId) ?? id
        ticker = try container.decodeIfPresent(String.self, forKey: .ticker)
        tickers = try container.decodeFlexibleStringArrayIfPresent(forKey: .tickers) ?? []
        title = try container.decodeIfPresent(String.self, forKey: .title) ?? ""
        summary = try container.decodeIfPresent(String.self, forKey: .summary)
        body = try container.decodeIfPresent(String.self, forKey: .body)
        source = try container.decodeIfPresent(String.self, forKey: .source)
        url = try container.decodeIfPresent(String.self, forKey: .url)
        publishedAt = try container.decodeIfPresent(Date.self, forKey: .publishedAt)
        category = NewsCategory(rawValue: (try container.decodeIfPresent(String.self, forKey: .category) ?? "market").lowercased()) ?? .market
        relevance = try container.decodeIfPresent(String.self, forKey: .relevance)
        grade = try container.decodeIfPresent(String.self, forKey: .grade)
        previousGrade = try container.decodeIfPresent(String.self, forKey: .previousGrade)
        currentGrade = try container.decodeIfPresent(String.self, forKey: .currentGrade)
        factored = (try? container.decode(Bool.self, forKey: .factored)) ?? false
        impact = try container.decodeIfPresent(String.self, forKey: .impact)
        heldShares = try container.decodeFlexibleDoubleIfPresent(forKey: .heldShares)
        positionId = try container.decodeIfPresent(String.self, forKey: .positionId)
        analysisRunId = try container.decodeIfPresent(String.self, forKey: .analysisRunId)
        imageUrl = try container.decodeIfPresent(String.self, forKey: .imageUrl)
    }

    var articleBody: String {
        if let body, !body.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return body
        }
        return summary ?? ""
    }

    var displayTimestamp: String {
        guard let publishedAt else { return "" }
        return publishedAt.formatted(date: .abbreviated, time: .shortened)
    }
}

enum NewsCategory: String, Codable, CaseIterable {
    case all
    case portfolio
    case watchlist
    case market
    case major

    var title: String {
        switch self {
        case .all: return "All"
        case .portfolio: return "Portfolio"
        case .watchlist: return "Watchlist"
        case .market: return "Market"
        case .major: return "Major"
        }
    }
}
