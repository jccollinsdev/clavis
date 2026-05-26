import XCTest
@testable import Clavis

final class PositionDecoderTests: XCTestCase {
    func testPositionDecodesNestedPreviousCloseFromSharedAnalysis() throws {
        let json = """
        {
          "id": "pos_1",
          "user_id": "user_1",
          "ticker": "AAPL",
          "shares": 10,
          "purchase_price": 150,
          "archetype": "growth",
          "created_at": "2026-05-26T10:00:00Z",
          "updated_at": "2026-05-26T10:00:00Z",
          "shared_analysis": {
            "ticker": "AAPL",
            "current_score": 84,
            "current_grade": "AA",
            "freshness": {
              "status": "fresh"
            },
            "previous_close": 198.42
          }
        }
        """

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        let position = try decoder.decode(Position.self, from: Data(json.utf8))

        XCTAssertEqual(position.sharedAnalysis?.previousClose ?? 0, 198.42, accuracy: 0.0001)
    }
}
