# Endpoint Verification

- User context: `90b7281c-0015-49de-a657-587bb25fbc6c`

## General Endpoints
- `/tickers/search?q=AAPL&limit=3` -> `200`
- `/holdings` -> `200`
- `/digest` -> `200`
- `/alerts` -> `200`

## Sample Tickers
### AAPL
- `/tickers/AAPL` -> `200`
- `/tickers/AAPL/methodology` -> `200`
- Detail grade/composite: `BBB` / `63.2`
- Detail dimensions: `{"financial_health": 62, "macro_exposure": 67, "news_sentiment": 53, "sector_exposure": 68, "volatility": 66}`
- Equal-weight average of available dimensions: `63.2`
- Methodology dimension scores: `{"financial_health": 62, "macro_exposure": 67, "news_sentiment": 53, "sector_exposure": 68, "volatility": 66}`

### MSFT
- `/tickers/MSFT` -> `200`
- `/tickers/MSFT/methodology` -> `200`
- Detail grade/composite: `BBB` / `65.8`
- Detail dimensions: `{"financial_health": 72, "macro_exposure": 67, "news_sentiment": 56, "sector_exposure": 68, "volatility": 66}`
- Equal-weight average of available dimensions: `65.8`
- Methodology dimension scores: `{"financial_health": 72, "macro_exposure": 67, "news_sentiment": 56, "sector_exposure": 68, "volatility": 66}`

### NVDA
- `/tickers/NVDA` -> `200`
- `/tickers/NVDA/methodology` -> `200`
- Detail grade/composite: `BB` / `53.6`
- Detail dimensions: `{"financial_health": 76, "macro_exposure": 41, "news_sentiment": 40, "sector_exposure": 68, "volatility": 43}`
- Equal-weight average of available dimensions: `53.6`
- Methodology dimension scores: `{"financial_health": 76, "macro_exposure": 41, "news_sentiment": 40, "sector_exposure": 68, "volatility": 43}`

### JPM
- `/tickers/JPM` -> `200`
- `/tickers/JPM/methodology` -> `200`
- Detail grade/composite: `BB` / `59.8`
- Detail dimensions: `{"financial_health": 56, "macro_exposure": 67, "news_sentiment": 41, "sector_exposure": 68, "volatility": 67}`
- Equal-weight average of available dimensions: `59.8`
- Methodology dimension scores: `{"financial_health": 56, "macro_exposure": 67, "news_sentiment": 41, "sector_exposure": 68, "volatility": 67}`

### XOM
- `/tickers/XOM` -> `200`
- `/tickers/XOM/methodology` -> `200`
- Detail grade/composite: `BBB` / `66.4`
- Detail dimensions: `{"financial_health": 72, "macro_exposure": 78, "news_sentiment": 42, "sector_exposure": 64, "volatility": 76}`
- Equal-weight average of available dimensions: `66.4`
- Methodology dimension scores: `{"financial_health": 72, "macro_exposure": 78, "news_sentiment": 42, "sector_exposure": 64, "volatility": 76}`

### JNJ
- `/tickers/JNJ` -> `200`
- `/tickers/JNJ/methodology` -> `200`
- Detail grade/composite: `BBB` / `67.6`
- Detail dimensions: `{"financial_health": 68, "macro_exposure": 78, "news_sentiment": 49, "sector_exposure": 68, "volatility": 75}`
- Equal-weight average of available dimensions: `67.6`
- Methodology dimension scores: `{"financial_health": 68, "macro_exposure": 78, "news_sentiment": 49, "sector_exposure": 68, "volatility": 75}`

### HIMS
- `/tickers/HIMS` -> `200`
- `/tickers/HIMS/methodology` -> `200`
- Detail grade/composite: `BB` / `51.0`
- Detail dimensions: `{"financial_health": 58, "macro_exposure": 41, "news_sentiment": null, "sector_exposure": 65, "volatility": 40}`
- Equal-weight average of available dimensions: `51`
- Methodology news sentiment limited reason: `Only 0 shared ticker event(s) were available in the last 7 days; at least 3 are required for a scored news sentiment dimension.`

### SPY
- `/tickers/SPY` -> `400`
- `/tickers/SPY/methodology` -> `200`
- Methodology dimension scores: `{"financial_health": null, "macro_exposure": null, "news_sentiment": null, "sector_exposure": null, "volatility": null}`
- Raw response detail: `{'detail_status': 400, 'methodology_status': 200, 'methodology_dimensions': {'financial_health': {'score': None, 'limited_data': False, 'limited_reason': None}, 'news_sentiment': {'score': None, 'limited_data': False, 'limited_reason': None}, 'macro_exposure': {'score': None, 'limited_data': False, 'limited_reason': None}, 'sector_exposure': {'score': None, 'limited_data': False, 'limited_reason': None}, 'volatility': {'score': None, 'limited_data': False, 'limited_reason': None}}}`

