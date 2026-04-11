import Foundation

struct PricePoint: Identifiable, Codable {
    let id: String
    let ticker: String
    let price: Double
    let recordedAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case ticker
        case price
        case recordedAt = "recorded_at"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decodeIfPresent(String.self, forKey: .id) ?? UUID().uuidString
        ticker = try container.decode(String.self, forKey: .ticker)
        price = try container.decodeFlexibleDouble(forKey: .price)

        let dateStr = try container.decode(String.self, forKey: .recordedAt)
        recordedAt = FlexibleDateDecoder.decode(dateStr) ?? Date()
    }
}

struct PriceHistoryResponse: Codable {
    let ticker: String
    let prices: [PricePoint]
}
