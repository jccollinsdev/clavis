import Foundation

private func parseNewsDate(_ raw: String?) -> Date? {
    guard let raw else { return nil }

    let iso8601Fractional = ISO8601DateFormatter()
    iso8601Fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    if let date = iso8601Fractional.date(from: raw) {
        return date
    }

    let iso8601Basic = ISO8601DateFormatter()
    iso8601Basic.formatOptions = [.withInternetDateTime]
    if let date = iso8601Basic.date(from: raw) {
        return date
    }

    let postgresFractional = DateFormatter()
    postgresFractional.locale = Locale(identifier: "en_US_POSIX")
    postgresFractional.dateFormat = "yyyy-MM-dd HH:mm:ss.SSSSSSXXXXX"
    if let date = postgresFractional.date(from: raw) {
        return date
    }

    let postgresBasic = DateFormatter()
    postgresBasic.locale = Locale(identifier: "en_US_POSIX")
    postgresBasic.dateFormat = "yyyy-MM-dd HH:mm:ssXXXXX"
    return postgresBasic.date(from: raw)
}

struct NewsItem: Identifiable, Codable {
    let id: String
    let userId: String
    let ticker: String?
    let title: String
    let summary: String?
    let source: String?
    let url: String?
    let significance: String?
    let publishedAt: Date?
    let affectedTickers: [String]?
    let processedAt: Date?

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case ticker
        case title
        case summary
        case source
        case url
        case significance
        case publishedAt = "published_at"
        case affectedTickers = "affected_tickers"
        case processedAt = "processed_at"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        userId = try container.decode(String.self, forKey: .userId)
        ticker = try container.decodeIfPresent(String.self, forKey: .ticker)
        title = try container.decode(String.self, forKey: .title)
        summary = try container.decodeIfPresent(String.self, forKey: .summary)
        source = try container.decodeIfPresent(String.self, forKey: .source)
        url = try container.decodeIfPresent(String.self, forKey: .url)
        significance = try container.decodeIfPresent(String.self, forKey: .significance)

        if let publishedAtString = try container.decodeIfPresent(String.self, forKey: .publishedAt) {
            publishedAt = parseNewsDate(publishedAtString)
        } else {
            publishedAt = try container.decodeIfPresent(Date.self, forKey: .publishedAt)
        }

        affectedTickers = try container.decodeIfPresent([String].self, forKey: .affectedTickers)

        if let processedAtString = try container.decodeIfPresent(String.self, forKey: .processedAt) {
            processedAt = parseNewsDate(processedAtString)
        } else {
            processedAt = try container.decodeIfPresent(Date.self, forKey: .processedAt)
        }
    }
}
