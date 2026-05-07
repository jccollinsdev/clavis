// wf-screens.jsx — all non-ticker, non-digest screens
// Changes from v1:
//   - Score History section REMOVED entirely
//   - Alerts: each item taps through to source; digest-ready alert added
//   - Article detail: "LLM reasoning" → "Why this score?" hidden behind tap
//   - Methodology: formula removed; 4 full audit pages added
//     (Financial Health · Macro Exposure · Sector Exposure · Volatility)

// ────────────── Shared mini bar chart for distribution ──────────────
function DistributionChart({ buckets, highlight }) {
  // buckets: array of {label, count}
  const max = Math.max(...buckets.map(b => b.count), 1);
  return (
    <div style={{ display: 'flex', gap: 3, alignItems: 'flex-end', height: 52 }}>
      {buckets.map((b, i) => (
        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
          <div style={{ width: '100%', height: `${Math.round((b.count / max) * 44)}px`, background: b.label === highlight ? WF.ink : WF.ink3, minHeight: b.count > 0 ? 3 : 0 }} />
          <span className="mono" style={{ fontSize: 8, color: WF.ink3 }}>{b.label}</span>
        </div>
      ))}
    </div>
  );
}

// ────────────── Article Table (shared across audit pages) ──────────────
function ArticleTable({ rows }) {
  // rows: [src, headline, score, w_R, w_T]
  return (
    <table style={{ width: 'calc(100% - 32px)', margin: '0 16px', borderCollapse: 'collapse', fontSize: 11 }}>
      <thead>
        <tr style={{ borderBottom: `1.5px solid ${WF.ink}` }}>
          {['SRC', 'HEADLINE', 'S', 'w_R', 'w_T'].map(h => (
            <th key={h} className="mono" style={{ padding: '4px 4px', textAlign: h === 'SRC' || h === 'HEADLINE' ? 'left' : 'right', fontSize: 9, color: WF.ink3, letterSpacing: 0.5, fontWeight: 600 }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody className="mono">
        {rows.map((r, i) => (
          <tr key={i} style={{ borderBottom: `1px solid ${WF.rule2}` }}>
            <td style={{ padding: '5px 4px', color: WF.ink3, whiteSpace: 'nowrap' }}>{r[0]}</td>
            <td style={{ padding: '5px 4px', fontSize: 11, fontFamily: WF.sans, maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r[1]}</td>
            <td style={{ padding: '5px 4px', textAlign: 'right', fontWeight: 700, color: r[2] < 50 ? WF.bad : WF.ink }}>{r[2]}</td>
            <td style={{ padding: '5px 4px', textAlign: 'right', color: WF.ink3 }}>{r[3]}</td>
            <td style={{ padding: '5px 4px', textAlign: 'right', color: WF.ink3 }}>{r[4]}</td>
          </tr>
        ))}
        <tr style={{ borderTop: `1.5px solid ${WF.ink}` }}>
          <td colSpan={2} style={{ padding: '5px 4px', fontWeight: 700 }}>weighted mean</td>
          <td style={{ padding: '5px 4px', textAlign: 'right', fontWeight: 700 }}>{rows[rows.length - 1][2] === '—' ? rows.slice(0,-1).reduce((s,r)=>s+r[2],0) / (rows.length-1) | 0 : rows[rows.length-1][2]}</td>
          <td colSpan={2} />
        </tr>
      </tbody>
    </table>
  );
}

// ────────────── Portfolio / Holdings + Watchlist ──────────────
function Portfolio() {
  const holdings = [
    { tkr: 'VOO',  name: 'Vanguard S&P 500', shares: 1240, price: 512.40, value: 635376, pnl: 12.6, grade: 'AAA', score: 93, dG: 0,  weight: 22.0 },
    { tkr: 'AAPL', name: 'Apple Inc.',        shares: 1850, price: 218.10, value: 403485, pnl: 53.1, grade: 'AAA', score: 91, dG: 0,  weight: 11.4 },
    { tkr: 'MSFT', name: 'Microsoft',         shares: 720,  price: 446.20, value: 321264, pnl: 43.0, grade: 'AAA', score: 90, dG: 0,  weight: 9.1  },
    { tkr: 'NVDA', name: 'NVIDIA',            shares: 308,  price: 942.18, value: 290191, pnl: 96.3, grade: 'A',   score: 74, dG: -1, weight: 8.2, alert: true },
    { tkr: 'TLT',  name: '20+Y Treasury',     shares: 2400, price: 88.50,  value: 212400, pnl: -3.9, grade: 'AA',  score: 80, dG: +1, weight: 6.0  },
    { tkr: 'XOM',  name: 'Exxon Mobil',       shares: 1620, price: 117.80, value: 190836, pnl: 22.2, grade: 'AA',  score: 82, dG: 0,  weight: 5.4  },
    { tkr: 'JPM',  name: 'JPMorgan',          shares: 780,  price: 218.90, value: 170742, pnl: 38.6, grade: 'AA',  score: 84, dG: 0,  weight: 4.8  },
  ];
  const total = holdings.reduce((s, h) => s + h.value, 0);
  return (
    <WFScreen>
      <WFAppBar title="Holdings" subtitle={`7 POSITIONS · $${(total / 1e6).toFixed(2)}M`} leading={<span className="mono" style={{ fontSize: 16 }}>≡</span>} trailing={<span className="mono" style={{ fontSize: 16 }}>+</span>} />
      <div style={{ padding: '14px 16px 12px', borderBottom: `1px solid ${WF.rule}`, display: 'flex', alignItems: 'center', gap: 12 }}>
        <WFGrade grade="AA" size="lg" delta={0} />
        <div style={{ flex: 1 }}>
          <WFEyebrow>Portfolio composite · weighted</WFEyebrow>
          <div className="mono" style={{ fontSize: 22, fontWeight: 600, marginTop: 2 }}>81/100</div>
          <div className="mono" style={{ fontSize: 11, color: WF.ink3 }}>▼ 1 from yesterday · NVDA</div>
        </div>
        <WFSparkline data={[88, 86, 85, 83, 84, 83, 82, 82, 81]} width={60} height={28} />
      </div>
      <div className="mono" style={{ padding: '8px 16px', display: 'flex', gap: 12, fontSize: 11, color: WF.ink3, borderBottom: `1px solid ${WF.rule2}` }}>
        <span style={{ color: WF.ink, borderBottom: `1.5px solid ${WF.ink}`, paddingBottom: 4 }}>Weight</span>
        <span>Grade</span><span>Δ</span><span>P/L</span>
      </div>
      <div>
        {holdings.map(h => (
          <div key={h.tkr} style={{ padding: '12px 16px', borderBottom: `1px solid ${WF.rule2}`, display: 'flex', alignItems: 'center', gap: 10, background: h.alert ? WF.warnSoft : WF.paper }}>
            <WFGrade grade={h.grade} size="xs" delta={h.dG} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span className="mono" style={{ fontSize: 13, fontWeight: 700 }}>{h.tkr}</span>
                <span style={{ fontSize: 11, color: WF.ink3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{h.name}</span>
              </div>
              <div className="mono" style={{ fontSize: 10, color: WF.ink3, marginTop: 2 }}>{h.shares.toLocaleString()} sh · ${h.price.toFixed(2)} · {h.weight}%</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div className="mono" style={{ fontSize: 13, fontWeight: 600 }}>${(h.value / 1000).toFixed(0)}k</div>
              <div className="mono" style={{ fontSize: 10, color: h.pnl > 0 ? WF.good : WF.bad, marginTop: 1 }}>{h.pnl > 0 ? '+' : ''}{h.pnl.toFixed(1)}%</div>
            </div>
          </div>
        ))}
      </div>
      <div style={{ padding: '20px 16px 6px', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <WFEyebrow>Watchlist · 3 of 5 free</WFEyebrow>
        <span className="mono" style={{ fontSize: 11, color: WF.ink3 }}>+ add</span>
      </div>
      <div>
        {[
          { tkr: 'GOOGL', name: 'Alphabet',     grade: 'A',   score: 73, dG: 0, ago: 'added 12d ago' },
          { tkr: 'TSM',   name: 'Taiwan Semi',  grade: 'AA',  score: 81, dG: 0, ago: 'added 28d ago' },
          { tkr: 'COST',  name: 'Costco',       grade: 'AAA', score: 90, dG: 0, ago: 'added 3d ago'  },
        ].map(w => (
          <div key={w.tkr} style={{ padding: '10px 16px', borderBottom: `1px solid ${WF.rule2}`, display: 'flex', alignItems: 'center', gap: 10 }}>
            <WFGrade grade={w.grade} size="xs" delta={w.dG} />
            <div style={{ flex: 1 }}>
              <span className="mono" style={{ fontSize: 13, fontWeight: 700 }}>{w.tkr}</span>
              <span style={{ fontSize: 11, color: WF.ink3, marginLeft: 8 }}>{w.name}</span>
              <div className="mono" style={{ fontSize: 10, color: WF.ink4, marginTop: 1 }}>{w.ago}</div>
            </div>
            <span className="mono" style={{ fontSize: 11, color: WF.ink3 }}>watching</span>
          </div>
        ))}
      </div>
      <div style={{ height: 12 }} />
      <WFTabBar active="portfolio" />
    </WFScreen>
  );
}

// ────────────── Methodology · Drawer (quick view) ──────────────
function MethodologyDrawer() {
  return (
    <WFScreen scroll={false}>
      <div style={{ position: 'absolute', inset: 0, opacity: 0.35, filter: 'grayscale(1)', pointerEvents: 'none' }}>
        <WFAppBar title="NVDA" />
        <div style={{ padding: 20 }}><WFGrade grade="A" size="hero" /></div>
      </div>
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 34, top: 80,
        background: WF.paper, borderTop: `1.5px solid ${WF.ink}`,
        display: 'flex', flexDirection: 'column',
        boxShadow: '0 -8px 24px rgba(0,0,0,0.15)',
      }}>
        <div style={{ padding: '8px 16px', display: 'flex', justifyContent: 'center' }}>
          <div style={{ width: 44, height: 4, background: WF.rule, borderRadius: 2 }} />
        </div>
        <div style={{ padding: '4px 16px 12px', display: 'flex', alignItems: 'center', gap: 10, borderBottom: `1px solid ${WF.rule}` }}>
          <WFGrade grade="A" size="sm" delta={-1} />
          <div style={{ flex: 1 }}>
            <span className="mono" style={{ fontSize: 14, fontWeight: 700 }}>NVDA</span>
            <span style={{ fontSize: 11, color: WF.ink3, marginLeft: 6 }}>composite 74/100</span>
          </div>
          <span className="mono" style={{ fontSize: 11, color: WF.accent }}>full audit ↗</span>
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: '0 16px 16px' }}>
          <div style={{ padding: '12px 0 8px' }}><WFEyebrow>Tap a dimension to expand</WFEyebrow></div>
          {[
            { n: 'Financial Health', s: 84, src: 'Finnhub · Q1 25',        exp: false },
            { n: 'News Sentiment',   s: 58, src: '12 articles · 7d',       exp: true  },
            { n: 'Macro Exposure',   s: 68, src: 'Polygon · weekly',       exp: false },
            { n: 'Sector Exposure',  s: 71, src: 'Tech · XLK · 12h',      exp: false },
            { n: 'Volatility',       s: 89, src: 'Polygon · daily',        exp: false },
          ].map(d => (
            <div key={d.n} style={{ borderTop: `1px solid ${WF.rule2}` }}>
              <div style={{ display: 'flex', alignItems: 'center', padding: '12px 0' }}>
                <span style={{ flex: 1, fontSize: 13, fontWeight: d.exp ? 600 : 400 }}>{d.n}</span>
                <span className="mono" style={{ fontSize: 11, color: WF.ink3, marginRight: 10 }}>{d.src}</span>
                <span className="mono" style={{ fontSize: 14, fontWeight: 700, width: 28, textAlign: 'right' }}>{d.s}</span>
                <span className="mono" style={{ marginLeft: 8, color: WF.ink3 }}>{d.exp ? '−' : '+'}</span>
              </div>
              {d.exp && (
                <div style={{ padding: '0 0 14px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div className="mono" style={{ fontSize: 11, color: WF.ink2, lineHeight: 1.5 }}>
                    12 articles · weighted mean = <b>58</b> · was 71 (7d ago)
                  </div>
                  <DistributionChart
                    buckets={[{label:'0-20',count:1},{label:'20-40',count:3},{label:'40-60',count:5},{label:'60-80',count:2},{label:'80+',count:1}]}
                    highlight="20-40"
                  />
                  <button style={{ alignSelf: 'flex-start', fontSize: 11, color: WF.accent, fontFamily: WF.mono }}>full audit ↗</button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </WFScreen>
  );
}

// ────────────── Methodology Full Audit — News Sentiment ──────────────
function MethodologyAuditNews() {
  const NEWS_ROWS = [
    ['Reuters', 'EU widens NVIDIA antitrust probe…',             32, '3.0', '1.5'],
    ['WSJ',     'Cloud customers say contracts under review',    38, '3.0', '1.5'],
    ['BBG',     'NVIDIA: probe is "ordinary course"',            41, '2.0', '1.5'],
    ['SA',      'Q1 datacenter rev still likely +$2B',           64, '2.0', '1.0'],
    ['CNBC',    'Analysts split on antitrust impact',            55, '2.0', '1.0'],
    ['MW',      'Capex guide unchanged',                         60, '1.0', '1.0'],
    ['YF',      'Insider selling at routine pace',               52, '1.0', '1.0'],
  ];
  return (
    <WFScreen>
      <WFAppBar title="Methodology" subtitle="NVDA · NEWS SENTIMENT" leading={<span className="mono">‹</span>} trailing={<span className="mono" style={{ fontSize: 14 }}>?</span>} />
      <div style={{ padding: '14px 16px 8px', borderBottom: `1px solid ${WF.rule}` }}>
        <WFEyebrow>News Sentiment · 0–100</WFEyebrow>
        <div className="mono" style={{ fontSize: 36, fontWeight: 700, marginTop: 4 }}>58 <span style={{ fontSize: 14, color: WF.bad, fontWeight: 600 }}>▼ 13 in 7d</span></div>
        <div style={{ fontSize: 12, color: WF.ink3, marginTop: 2 }}>Last refreshed 3h ago · 12 articles in 7d window</div>
      </div>
      <div style={{ padding: '14px 16px 6px' }}><WFEyebrow>Score distribution · 12 articles</WFEyebrow></div>
      <div style={{ padding: '0 16px 8px' }}>
        <DistributionChart
          buckets={[{label:'0–20',count:1},{label:'20–40',count:3},{label:'40–60',count:5},{label:'60–80',count:2},{label:'80+',count:1}]}
          highlight="20–40"
        />
        <div className="mono" style={{ fontSize: 10, color: WF.ink3, marginTop: 4 }}>
          Weighted mean <b style={{ color: WF.ink }}>58.0</b> · volume 2.4× 4w avg — elevated
        </div>
      </div>
      <div style={{ padding: '10px 16px 6px' }}><WFEyebrow>Articles · 7d window</WFEyebrow></div>
      <ArticleTable rows={NEWS_ROWS} />
      <div style={{ padding: '12px 16px 6px' }}>
        <WFCallout>Volume signal active — coverage is 2.4× the 4-week average. Unusual attention is itself a risk signal.</WFCallout>
      </div>
      <div style={{ padding: '8px 16px 6px' }}>
        <button style={{ fontSize: 12, color: WF.ink3, fontFamily: WF.mono }}>+ 5 more articles ›</button>
      </div>
      <div style={{ height: 16 }} />
      <WFTabBar active="search" />
    </WFScreen>
  );
}

// ────────────── Methodology Full Audit — Financial Health ──────────────
function MethodologyAuditFinHealth() {
  const FH_ROWS = [
    ['Finnhub', 'D/E ratio: 0.41 (vs sector avg 1.2)',           88, 'N/A', 'N/A'],
    ['Finnhub', 'FCF margin: 41% (vs sector avg 18%)',           91, 'N/A', 'N/A'],
    ['Finnhub', 'Interest coverage: 38× (vs threshold 3×)',      95, 'N/A', 'N/A'],
    ['Finnhub', 'Current ratio: 4.1 (vs threshold 1.5)',         90, 'N/A', 'N/A'],
    ['Finnhub', 'Revenue growth 4Q avg: +95%',                   89, 'N/A', 'N/A'],
    ['Finnhub', 'Net income: positive × 12 consecutive quarters',86, 'N/A', 'N/A'],
    ['Finnhub', 'Altman Z-score: 8.2 (safe zone > 2.99)',        78, 'N/A', 'N/A'],
  ];
  return (
    <WFScreen>
      <WFAppBar title="Methodology" subtitle="NVDA · FINANCIAL HEALTH" leading={<span className="mono">‹</span>} trailing={<span className="mono" style={{ fontSize: 14 }}>?</span>} />
      <div style={{ padding: '14px 16px 8px', borderBottom: `1px solid ${WF.rule}` }}>
        <WFEyebrow>Financial Health · 0–100</WFEyebrow>
        <div className="mono" style={{ fontSize: 36, fontWeight: 700, marginTop: 4 }}>84 <span style={{ fontSize: 14, color: WF.good, fontWeight: 600 }}>▲ 1 in 7d</span></div>
        <div style={{ fontSize: 12, color: WF.ink3, marginTop: 2 }}>Source: Finnhub fundamentals · Q1 2025 filing · refreshed quarterly</div>
      </div>
      <div style={{ padding: '14px 16px 6px' }}><WFEyebrow>Input score distribution</WFEyebrow></div>
      <div style={{ padding: '0 16px 8px' }}>
        <DistributionChart
          buckets={[{label:'0–20',count:0},{label:'20–40',count:0},{label:'40–60',count:0},{label:'60–80',count:1},{label:'80+',count:6}]}
          highlight="80+"
        />
        <div className="mono" style={{ fontSize: 10, color: WF.ink3, marginTop: 4 }}>
          Weighted mean <b style={{ color: WF.ink }}>84.0</b> · all signals strong · no distress flags
        </div>
      </div>
      <div style={{ padding: '10px 16px 6px' }}><WFEyebrow>Inputs · Q1 2025 · 7 signals</WFEyebrow></div>
      <div style={{ padding: '0 16px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: `1.5px solid ${WF.ink}` }}>
              {['SIGNAL', 'VALUE', 'SCORE', 'WEIGHT'].map(h => (
                <th key={h} className="mono" style={{ padding: '5px 4px', textAlign: h === 'SIGNAL' ? 'left' : 'right', fontSize: 9, color: WF.ink3, letterSpacing: 0.5 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ['D/E ratio',       '0.41',    88, '20%'],
              ['FCF margin',      '41%',     91, '20%'],
              ['Interest cov.',   '38×',     95, '15%'],
              ['Current ratio',   '4.1',     90, '15%'],
              ['Revenue growth',  '+95%',    89, '15%'],
              ['Net income',      'pos 12Q', 86, '10%'],
              ['Altman Z',        '8.2',     78,  '5%'],
            ].map(([sig, val, sc, wt], i) => (
              <tr key={i} style={{ borderBottom: `1px solid ${WF.rule2}` }}>
                <td style={{ padding: '7px 4px', fontSize: 12 }}>{sig}</td>
                <td className="mono" style={{ padding: '7px 4px', textAlign: 'right', color: WF.ink2 }}>{val}</td>
                <td className="mono" style={{ padding: '7px 4px', textAlign: 'right', fontWeight: 700, color: sc >= 80 ? WF.good : sc >= 60 ? WF.ink : WF.bad }}>{sc}</td>
                <td className="mono" style={{ padding: '7px 4px', textAlign: 'right', color: WF.ink3 }}>{wt}</td>
              </tr>
            ))}
            <tr style={{ borderTop: `1.5px solid ${WF.ink}` }}>
              <td colSpan={2} style={{ padding: '5px 4px', fontWeight: 700, fontSize: 12 }}>weighted mean</td>
              <td className="mono" style={{ padding: '5px 4px', textAlign: 'right', fontWeight: 700 }}>84.0</td>
              <td />
            </tr>
          </tbody>
        </table>
      </div>
      <div style={{ padding: '12px 16px 16px' }}>
        <WFCallout>Financial Health updates quarterly (on filing). Next update: Q2 2025 earnings ~Aug.</WFCallout>
      </div>
      <WFTabBar active="search" />
    </WFScreen>
  );
}

// ────────────── Methodology Full Audit — Macro Exposure ──────────────
function MethodologyAuditMacro() {
  const MACRO_ROWS = [
    ['Polygon', 'Beta vs S&P 500 (60d): 1.72',                   55, 'N/A', 'N/A'],
    ['Polygon', 'Rate sensitivity: −0.31 per 10bp yield rise',   58, 'N/A', 'N/A'],
    ['Polygon', 'Dollar correlation (DXY 90d): −0.44',           65, 'N/A', 'N/A'],
    ['FRED',    'PMI regime: expansion (53.2)',                   80, 'N/A', 'N/A'],
    ['FRED',    'Yield curve: flat at −12bp (2s10s)',            62, 'N/A', 'N/A'],
    ['Polygon', 'VIX regime: low (14.8)',                         82, 'N/A', 'N/A'],
  ];
  return (
    <WFScreen>
      <WFAppBar title="Methodology" subtitle="NVDA · MACRO EXPOSURE" leading={<span className="mono">‹</span>} trailing={<span className="mono" style={{ fontSize: 14 }}>?</span>} />
      <div style={{ padding: '14px 16px 8px', borderBottom: `1px solid ${WF.rule}` }}>
        <WFEyebrow>Macro Exposure · 0–100</WFEyebrow>
        <div className="mono" style={{ fontSize: 36, fontWeight: 700, marginTop: 4 }}>68 <span style={{ fontSize: 14, color: WF.ink3, fontWeight: 600 }}>— unchanged</span></div>
        <div style={{ fontSize: 12, color: WF.ink3, marginTop: 2 }}>Sources: Polygon · FRED · refreshed 12h ago</div>
      </div>
      <div style={{ padding: '14px 16px 6px' }}><WFEyebrow>Score distribution · 6 signals</WFEyebrow></div>
      <div style={{ padding: '0 16px 8px' }}>
        <DistributionChart
          buckets={[{label:'0–20',count:0},{label:'20–40',count:0},{label:'40–60',count:2},{label:'60–80',count:3},{label:'80+',count:1}]}
          highlight="60–80"
        />
        <div className="mono" style={{ fontSize: 10, color: WF.ink3, marginTop: 4 }}>
          Weighted mean <b style={{ color: WF.ink }}>68.0</b> · high beta is the primary drag
        </div>
      </div>
      <div style={{ padding: '10px 16px 6px' }}><WFEyebrow>Inputs · 6 macro signals</WFEyebrow></div>
      <div style={{ padding: '0 16px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: `1.5px solid ${WF.ink}` }}>
              {['SIGNAL', 'VALUE', 'SCORE', 'WEIGHT'].map(h => (
                <th key={h} className="mono" style={{ padding: '5px 4px', textAlign: h === 'SIGNAL' ? 'left' : 'right', fontSize: 9, color: WF.ink3, letterSpacing: 0.5 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ['Beta (60d)',        '1.72',   55, '30%'],
              ['Rate sensitivity',  '−0.31',  58, '25%'],
              ['Dollar corr.',      '−0.44',  65, '15%'],
              ['PMI regime',        '53.2',   80, '15%'],
              ['Yield curve',       '−12bp',  62, '10%'],
              ['VIX regime',        '14.8',   82,  '5%'],
            ].map(([sig, val, sc, wt], i) => (
              <tr key={i} style={{ borderBottom: `1px solid ${WF.rule2}` }}>
                <td style={{ padding: '7px 4px', fontSize: 12 }}>{sig}</td>
                <td className="mono" style={{ padding: '7px 4px', textAlign: 'right', color: WF.ink2 }}>{val}</td>
                <td className="mono" style={{ padding: '7px 4px', textAlign: 'right', fontWeight: 700, color: sc >= 75 ? WF.good : sc >= 55 ? WF.ink : WF.bad }}>{sc}</td>
                <td className="mono" style={{ padding: '7px 4px', textAlign: 'right', color: WF.ink3 }}>{wt}</td>
              </tr>
            ))}
            <tr style={{ borderTop: `1.5px solid ${WF.ink}` }}>
              <td colSpan={2} style={{ padding: '5px 4px', fontWeight: 700, fontSize: 12 }}>weighted mean</td>
              <td className="mono" style={{ padding: '5px 4px', textAlign: 'right', fontWeight: 700 }}>68.0</td>
              <td />
            </tr>
          </tbody>
        </table>
      </div>
      <div style={{ padding: '12px 16px 16px' }}>
        <WFCallout>High beta (1.72) is the primary macro drag. NVDA is more sensitive to macro shocks than 80% of universe. CPI today is a live risk.</WFCallout>
      </div>
      <WFTabBar active="search" />
    </WFScreen>
  );
}

// ────────────── Methodology Full Audit — Sector Exposure ──────────────
function MethodologyAuditSector() {
  return (
    <WFScreen>
      <WFAppBar title="Methodology" subtitle="NVDA · SECTOR EXPOSURE" leading={<span className="mono">‹</span>} trailing={<span className="mono" style={{ fontSize: 14 }}>?</span>} />
      <div style={{ padding: '14px 16px 8px', borderBottom: `1px solid ${WF.rule}` }}>
        <WFEyebrow>Sector Exposure · 0–100</WFEyebrow>
        <div className="mono" style={{ fontSize: 36, fontWeight: 700, marginTop: 4 }}>71 <span style={{ fontSize: 14, color: WF.ink3, fontWeight: 600 }}>— unchanged</span></div>
        <div style={{ fontSize: 12, color: WF.ink3, marginTop: 2 }}>Sources: Polygon · XLK · SOXX · refreshed 6h ago</div>
      </div>
      <div style={{ padding: '14px 16px 6px' }}><WFEyebrow>Score distribution · 5 signals</WFEyebrow></div>
      <div style={{ padding: '0 16px 8px' }}>
        <DistributionChart
          buckets={[{label:'0–20',count:0},{label:'20–40',count:0},{label:'40–60',count:1},{label:'60–80',count:3},{label:'80+',count:1}]}
          highlight="60–80"
        />
        <div className="mono" style={{ fontSize: 10, color: WF.ink3, marginTop: 4 }}>
          Weighted mean <b style={{ color: WF.ink }}>71.0</b> · sector momentum positive; concentration a drag
        </div>
      </div>
      <div style={{ padding: '10px 16px 6px' }}><WFEyebrow>Inputs · 5 sector signals</WFEyebrow></div>
      <div style={{ padding: '0 16px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: `1.5px solid ${WF.ink}` }}>
              {['SIGNAL', 'VALUE', 'SCORE', 'WEIGHT'].map(h => (
                <th key={h} className="mono" style={{ padding: '5px 4px', textAlign: h === 'SIGNAL' ? 'left' : 'right', fontSize: 9, color: WF.ink3, letterSpacing: 0.5 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ['XLK 5d momentum',     '+1.8%',   78, '30%'],
              ['SOXX 5d momentum',    '+0.4%',   65, '25%'],
              ['Sector rel. strength','1.12 vs SPY', 72, '20%'],
              ['Sector vol. regime',  'low',     80, '15%'],
              ['Concentration risk',  'top 3 = 52%',  55, '10%'],
            ].map(([sig, val, sc, wt], i) => (
              <tr key={i} style={{ borderBottom: `1px solid ${WF.rule2}` }}>
                <td style={{ padding: '7px 4px', fontSize: 12 }}>{sig}</td>
                <td className="mono" style={{ padding: '7px 4px', textAlign: 'right', color: WF.ink2 }}>{val}</td>
                <td className="mono" style={{ padding: '7px 4px', textAlign: 'right', fontWeight: 700, color: sc >= 75 ? WF.good : sc >= 55 ? WF.ink : WF.bad }}>{sc}</td>
                <td className="mono" style={{ padding: '7px 4px', textAlign: 'right', color: WF.ink3 }}>{wt}</td>
              </tr>
            ))}
            <tr style={{ borderTop: `1.5px solid ${WF.ink}` }}>
              <td colSpan={2} style={{ padding: '5px 4px', fontWeight: 700, fontSize: 12 }}>weighted mean</td>
              <td className="mono" style={{ padding: '5px 4px', textAlign: 'right', fontWeight: 700 }}>71.0</td>
              <td />
            </tr>
          </tbody>
        </table>
      </div>
      <div style={{ padding: '12px 16px 16px' }}>
        <WFCallout>Tech sector momentum is positive but concentration is elevated — top 3 names are 52% of XLK. NVDA is one of those top 3, amplifying both upside and downside.</WFCallout>
      </div>
      <WFTabBar active="search" />
    </WFScreen>
  );
}

// ────────────── Methodology Full Audit — Volatility ──────────────
function MethodologyAuditVolatility() {
  return (
    <WFScreen>
      <WFAppBar title="Methodology" subtitle="NVDA · VOLATILITY" leading={<span className="mono">‹</span>} trailing={<span className="mono" style={{ fontSize: 14 }}>?</span>} />
      <div style={{ padding: '14px 16px 8px', borderBottom: `1px solid ${WF.rule}` }}>
        <WFEyebrow>Volatility · 0–100 (higher = lower vol = better)</WFEyebrow>
        <div className="mono" style={{ fontSize: 36, fontWeight: 700, marginTop: 4 }}>89 <span style={{ fontSize: 14, color: WF.good, fontWeight: 600 }}>▲ 2 in 7d</span></div>
        <div style={{ fontSize: 12, color: WF.ink3, marginTop: 2 }}>Source: Polygon options + price · refreshed EOD</div>
      </div>
      <div style={{ padding: '14px 16px 6px' }}><WFEyebrow>Score distribution · 5 signals</WFEyebrow></div>
      <div style={{ padding: '0 16px 8px' }}>
        <DistributionChart
          buckets={[{label:'0–20',count:0},{label:'20–40',count:0},{label:'40–60',count:0},{label:'60–80',count:1},{label:'80+',count:4}]}
          highlight="80+"
        />
        <div className="mono" style={{ fontSize: 10, color: WF.ink3, marginTop: 4 }}>
          Weighted mean <b style={{ color: WF.ink }}>89.0</b> · realized vol falling; options calm
        </div>
      </div>
      <div style={{ padding: '10px 16px 6px' }}><WFEyebrow>Inputs · 5 volatility signals</WFEyebrow></div>
      <div style={{ padding: '0 16px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: `1.5px solid ${WF.ink}` }}>
              {['SIGNAL', 'VALUE', 'SCORE', 'WEIGHT'].map(h => (
                <th key={h} className="mono" style={{ padding: '5px 4px', textAlign: h === 'SIGNAL' ? 'left' : 'right', fontSize: 9, color: WF.ink3, letterSpacing: 0.5 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ['30d realized vol',    '28% (falling)',  88, '30%'],
              ['IV (at-money 30d)',   '31%',            85, '25%'],
              ['IV/RV ratio',         '1.11 (calm)',    87, '20%'],
              ['30d max drawdown',    '−11.4%',         78, '15%'],
              ['Put/call skew',       '−0.04 (neutral)',92, '10%'],
            ].map(([sig, val, sc, wt], i) => (
              <tr key={i} style={{ borderBottom: `1px solid ${WF.rule2}` }}>
                <td style={{ padding: '7px 4px', fontSize: 12 }}>{sig}</td>
                <td className="mono" style={{ padding: '7px 4px', textAlign: 'right', color: WF.ink2 }}>{val}</td>
                <td className="mono" style={{ padding: '7px 4px', textAlign: 'right', fontWeight: 700, color: sc >= 80 ? WF.good : sc >= 60 ? WF.ink : WF.bad }}>{sc}</td>
                <td className="mono" style={{ padding: '7px 4px', textAlign: 'right', color: WF.ink3 }}>{wt}</td>
              </tr>
            ))}
            <tr style={{ borderTop: `1.5px solid ${WF.ink}` }}>
              <td colSpan={2} style={{ padding: '5px 4px', fontWeight: 700, fontSize: 12 }}>weighted mean</td>
              <td className="mono" style={{ padding: '5px 4px', textAlign: 'right', fontWeight: 700 }}>89.0</td>
              <td />
            </tr>
          </tbody>
        </table>
      </div>
      <div style={{ padding: '12px 16px 16px' }}>
        <WFCallout>Volatility score inverted: 100 = perfectly calm. Score of 89 means NVDA is in the calmer 15% of the universe today. Realized vol is trending down post-earnings.</WFCallout>
      </div>
      <WFTabBar active="search" />
    </WFScreen>
  );
}

// ────────────── Article Detail ──────────────
function ArticleDetail() {
  const { useState } = React;
  const [showWhy, setShowWhy] = React.useState(false);
  return (
    <WFScreen>
      <WFAppBar title="Article" leading={<span className="mono">‹</span>} trailing={<span className="mono" style={{ fontSize: 14 }}>↗</span>} />
      <div style={{ padding: '14px 16px 6px' }}>
        <div className="mono" style={{ fontSize: 10, color: WF.ink3, display: 'flex', gap: 8 }}>
          <span style={{ color: WF.ink, fontWeight: 700 }}>REUTERS · T1</span>
          <span>·</span><span>3h ago</span>
          <span>·</span><span>regulatory</span>
        </div>
        <h1 style={{ fontSize: 22, fontWeight: 600, lineHeight: 1.2, letterSpacing: -0.2, margin: '8px 0 12px' }}>
          EU widens NVIDIA antitrust probe to cover enterprise GPU supply contracts
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: WF.ink3 }}>Sentiment</span>
          <div style={{ flex: 1, maxWidth: 120 }}><WFScoreBar score={32} height={5} /></div>
          <span className="mono" style={{ fontSize: 14, fontWeight: 700, color: WF.bad }}>32</span>
        </div>
      </div>

      <div style={{ padding: '14px 16px 6px' }}><WFEyebrow>TL;DR</WFEyebrow></div>
      <div style={{ padding: '0 16px', fontSize: 14, lineHeight: 1.5, color: WF.ink2 }}>
        EU competition commission expanded its existing NVIDIA review to include long-term GPU supply contracts with hyperscalers. No remedies proposed yet; investigation in early phase.
      </div>

      <div style={{ padding: '16px 16px 6px' }}><WFEyebrow>What it means · for your position</WFEyebrow></div>
      <div style={{ margin: '0 16px', padding: 12, background: WF.accentSoft, border: `1px solid #e8b890`, fontSize: 13, lineHeight: 1.5, color: WF.ink2 }}>
        You hold <b>308 shares</b> of NVDA at <b>$480 cost basis</b> — currently <b>+96% unrealized</b>. NVDA is <b>8.2% of your book</b>. Regulatory overhangs historically produce 60–180 day uncertainty windows.
      </div>

      <div style={{ padding: '16px 16px 6px' }}><WFEyebrow>Key implications</WFEyebrow></div>
      <ul style={{ padding: '0 16px 0 32px', fontSize: 13, lineHeight: 1.55, color: WF.ink2, margin: 0 }}>
        <li>Datacenter contract terms could be forced into modification</li>
        <li>Margin compression risk if exclusive deals are unwound</li>
        <li>Timeline: EU phase-1 reviews typically 25 working days</li>
        <li>Comp: 2024 AAPL App Store probe took 14 months to remedies</li>
      </ul>

      {/* WHY THIS SCORE — hidden by default */}
      <div style={{ padding: '16px 16px 6px' }}>
        <button
          onClick={() => setShowWhy(!showWhy)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            fontFamily: WF.mono, fontSize: 11, color: WF.ink3,
            padding: '6px 10px', border: `1px solid ${WF.rule}`, background: WF.paper2,
          }}
        >
          <span style={{ fontSize: 9 }}>{showWhy ? '▲' : '▼'}</span>
          Why this score?
        </button>
      </div>
      {showWhy && (
        <div style={{ margin: '0 16px 12px', padding: 10, border: `1px dashed ${WF.rule}`, background: WF.paper2, fontSize: 12, lineHeight: 1.5, color: WF.ink3, fontFamily: WF.mono }}>
          Headline framing: regulatory escalation. Direct revenue tie to the core GPU business. T1 source weighting upgrades signal credibility. No softening hedge in article body. Compares to recent large-cap tech regulatory escalations (median sentiment ~30).
        </div>
      )}

      <div style={{ padding: '8px 16px 24px' }}>
        <button style={{ width: '100%', padding: '12px 0', border: `1px solid ${WF.ink}`, fontSize: 13, fontWeight: 600 }}>Read at reuters.com ↗</button>
      </div>
      <WFTabBar active="search" />
    </WFScreen>
  );
}

// ────────────── Universal Search ──────────────
function Search() {
  return (
    <WFScreen>
      <div style={{ padding: '8px 16px 12px', display: 'flex', alignItems: 'center', gap: 8, borderBottom: `1px solid ${WF.rule}` }}>
        <span className="mono" style={{ fontSize: 14 }}>‹</span>
        <div style={{ flex: 1, height: 36, border: `1px solid ${WF.ink}`, padding: '0 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="mono" style={{ fontSize: 12, color: WF.ink3 }}>◯</span>
          <span className="mono" style={{ fontSize: 14 }}>nvi</span>
          <span style={{ width: 1, height: 16, background: WF.ink, animation: 'blink 1s step-end infinite' }} />
        </div>
        <span style={{ fontSize: 13, color: WF.accent }}>Cancel</span>
      </div>
      <div style={{ padding: '12px 16px 6px' }}><WFEyebrow>Top results</WFEyebrow></div>
      <div>
        {[
          { tkr: 'NVDA', name: 'NVIDIA Corporation', grade: 'A',   score: 74, price: 942.18, in: true  },
          { tkr: 'NVMI', name: 'Nova Ltd.',           grade: 'BBB', score: 64, price: 245.30, in: false },
          { tkr: 'NVO',  name: 'Novo Nordisk ADR',    grade: 'AA',  score: 83, price: 128.40, in: false },
        ].map(r => (
          <div key={r.tkr} style={{ padding: '12px 16px', borderBottom: `1px solid ${WF.rule2}`, display: 'flex', alignItems: 'center', gap: 10 }}>
            <WFGrade grade={r.grade} size="xs" />
            <div style={{ flex: 1 }}>
              <div><span className="mono" style={{ fontWeight: 700 }}>{r.tkr}</span> <span style={{ color: WF.ink3, fontSize: 12 }}>· {r.name}</span></div>
              <div className="mono" style={{ fontSize: 10, color: WF.ink3, marginTop: 2 }}>${r.price} · score {r.score}{r.in && <span style={{ color: WF.accent, fontWeight: 700 }}> · in your portfolio</span>}</div>
            </div>
            <span className="mono" style={{ fontSize: 11, color: WF.ink4 }}>›</span>
          </div>
        ))}
      </div>
      <div style={{ padding: '20px 16px 6px' }}><WFEyebrow>Outside universe</WFEyebrow></div>
      <div style={{ padding: '10px 16px', borderTop: `1px solid ${WF.rule2}`, borderBottom: `1px solid ${WF.rule2}` }}>
        <div className="mono" style={{ fontSize: 12, fontWeight: 700 }}>NVTS · Navitas Semiconductor</div>
        <div style={{ fontSize: 11, color: WF.ink3, marginTop: 2, lineHeight: 1.45 }}>Below $2B cap threshold. <span style={{ color: WF.accent, fontWeight: 600 }}>Add manually →</span></div>
      </div>
      <div style={{ padding: '20px 16px 6px' }}><WFEyebrow>Recent</WFEyebrow></div>
      <div className="mono" style={{ padding: '0 16px', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {['NVDA', 'GOOGL', 'TSM', 'XOM', 'TLT'].map(t => (
          <div key={t} style={{ padding: '4px 10px', border: `1px solid ${WF.rule}`, fontSize: 11 }}>{t}</div>
        ))}
      </div>
      <div style={{ height: 12 }} />
      <WFTabBar active="search" />
    </WFScreen>
  );
}

// ────────────── Alerts ──────────────
// Each alert has a destination tag so tap-through is clear.
function Alerts() {
  return (
    <WFScreen>
      <WFAppBar title="Alerts" subtitle="4 NEW · 13 LAST 30D" leading={<span className="mono">≡</span>} trailing={<span className="mono" style={{ fontSize: 12 }}>⊜</span>} />
      <div style={{ padding: '8px 16px', display: 'flex', gap: 12, fontSize: 12, color: WF.ink3, borderBottom: `1px solid ${WF.rule}` }}>
        <span style={{ color: WF.ink, fontWeight: 600, borderBottom: `1.5px solid ${WF.ink}`, paddingBottom: 4 }}>All</span>
        <span>Grade</span><span>News</span><span>Macro</span><span>Digest</span>
      </div>

      {[
        {
          time: '7:04 AM', kind: 'DIGEST READY', tkr: '—',
          body: 'Your May 6 morning briefing is ready. 1 grade change — NVDA.',
          sev: 'info', dest: '→ Today', destTag: 'digest', newAlert: true,
        },
        {
          time: '7:01 AM', kind: 'GRADE CHANGE', tkr: 'NVDA',
          body: 'Downgraded AA → A. 5-pt composite drop driven by news sentiment (71 → 58).',
          sev: 'high', dest: '→ NVDA', destTag: 'ticker', newAlert: true,
        },
        {
          time: '6:48 AM', kind: 'NEWS · HIGH-IMPACT', tkr: 'NVDA',
          body: 'Reuters: EU widens antitrust probe to cover enterprise GPU supply contracts.',
          sev: 'high', dest: '→ Article', destTag: 'article', newAlert: true,
        },
        {
          time: '6:12 AM', kind: 'MACRO', tkr: '—',
          body: '10Y yield drifted 4bp lower overnight. TLT score +1, no grade change.',
          sev: 'low', dest: '→ Today', destTag: 'digest', newAlert: true,
        },
        {
          time: 'Yest 5:14 PM', kind: 'NEWS', tkr: 'XOM',
          body: 'OPEC+ rollover headlines. Crude +1.8%. No score impact.',
          sev: 'low', dest: '→ Article', destTag: 'article', newAlert: false,
        },
        {
          time: 'Yest 9:22 AM', kind: 'PORTFOLIO', tkr: '—',
          body: 'Portfolio composite ▲ 1 to 82. Driven by TLT, JPM.',
          sev: 'low', dest: '→ Holdings', destTag: 'portfolio', newAlert: false,
        },
      ].map((a, i) => (
        <div key={i} style={{
          padding: '12px 16px', borderBottom: `1px solid ${WF.rule2}`,
          background: a.newAlert ? '#fdfbf2' : WF.paper, position: 'relative',
          display: 'flex', gap: 10, alignItems: 'flex-start',
        }}>
          {a.newAlert && <div style={{ position: 'absolute', left: 6, top: 20, width: 5, height: 5, borderRadius: '50%', background: WF.accent }} />}
          <div style={{ flex: 1 }}>
            <div className="mono" style={{ fontSize: 9, color: WF.ink3, letterSpacing: 0.6, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ fontWeight: 700, color: a.sev === 'high' ? WF.bad : a.sev === 'info' ? WF.accent : WF.ink2 }}>{a.kind}</span>
              {a.tkr !== '—' && <><span>·</span><span style={{ color: WF.ink }}>{a.tkr}</span></>}
              <span style={{ marginLeft: 'auto' }}>{a.time}</span>
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.45, color: WF.ink2, marginTop: 4 }}>{a.body}</div>
          </div>
          {/* Tap-through destination */}
          <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center' }}>
            <span className="mono" style={{ fontSize: 10, color: WF.ink3, border: `1px solid ${WF.rule}`, padding: '3px 6px', whiteSpace: 'nowrap' }}>{a.dest} ›</span>
          </div>
        </div>
      ))}

      <div style={{ padding: '20px 16px 24px' }}>
        <WFCallout>Quiet hours active 10pm – 7am. Alerts during quiet hours queue and deliver at 7:00. Digest-ready alerts are always delivered at 7:00 AM.</WFCallout>
      </div>
      <WFTabBar active="alerts" />
    </WFScreen>
  );
}

// ────────────── Onboarding A ──────────────
function OnboardA() {
  return (
    <WFScreen>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '40px 24px 24px' }}>
        <div style={{ flex: 1 }}>
          <div className="mono" style={{ fontSize: 12, color: WF.accent, letterSpacing: 1.5, fontWeight: 700 }}>CLAVIX</div>
          <div style={{ fontSize: 32, fontWeight: 600, lineHeight: 1.15, letterSpacing: -0.6, marginTop: 28 }}>Portfolio risk,<br />measured.</div>
          <div style={{ fontSize: 15, color: WF.ink2, lineHeight: 1.5, marginTop: 14 }}>
            Every morning, in 60 seconds: what changed overnight, what it means for your book, and a letter grade per position — with the math shown.
          </div>
          <div style={{ marginTop: 36, display: 'flex', flexDirection: 'column', gap: 14 }}>
            {[
              ['1', 'Bond-rating-style grades', 'AAA → F. Same scale you already trust.'],
              ['2', 'Five risk dimensions, audited', 'Every score is auditable. Tap any number.'],
              ['3', 'Personalised morning briefing', 'Tailored to your holdings — not a generic feed.'],
            ].map(([n, t, s]) => (
              <div key={n} style={{ display: 'flex', gap: 14 }}>
                <div className="mono" style={{ width: 28, height: 28, border: `1.5px solid ${WF.ink}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 13 }}>{n}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{t}</div>
                  <div style={{ fontSize: 12, color: WF.ink3, marginTop: 2 }}>{s}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
        <button style={{ width: '100%', padding: '14px 0', background: WF.ink, color: '#fff', fontWeight: 600, fontSize: 15 }}>Continue</button>
        <button style={{ marginTop: 8, fontSize: 12, color: WF.ink3 }}>Already have an account · Sign in</button>
      </div>
    </WFScreen>
  );
}

// ────────────── Onboarding B ──────────────
function OnboardB() {
  return (
    <WFScreen>
      <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className="mono" style={{ fontSize: 14, color: WF.ink3 }}>‹</span>
        <div className="mono" style={{ flex: 1, fontSize: 11, color: WF.ink3, letterSpacing: 0.6 }}>STEP 3 / 4</div>
        <span style={{ fontSize: 12, color: WF.ink3 }}>Skip</span>
      </div>
      <div style={{ padding: '0 16px' }}>
        <div style={{ height: 3, background: WF.rule2, position: 'relative' }}>
          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '75%', background: WF.ink }} />
        </div>
      </div>
      <div style={{ padding: '28px 24px 8px' }}>
        <div style={{ fontSize: 26, fontWeight: 600, lineHeight: 1.2, letterSpacing: -0.4 }}>Add your portfolio</div>
        <div style={{ fontSize: 14, color: WF.ink2, marginTop: 8, lineHeight: 1.5 }}>
          Connect your brokerage for read-only sync, paste a CSV, or enter holdings manually. <b>Clavix never has trading access.</b>
        </div>
      </div>
      <div style={{ padding: '16px 16px 8px' }}>
        {[
          { kind: 'Connect brokerage', sub: 'Fidelity · Schwab · Vanguard · IBKR · Merrill · E*TRADE', tag: 'PRO · read-only', best: true },
          { kind: 'Paste CSV', sub: 'Upload an export from your brokerage. Column-mapping wizard.', tag: 'PRO' },
          { kind: 'Enter manually', sub: 'Ticker · shares · cost basis. Up to 3 holdings on Free.', tag: 'FREE' },
        ].map(o => (
          <div key={o.kind} style={{ padding: 14, marginBottom: 10, border: `1.5px solid ${o.best ? WF.ink : WF.rule}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontWeight: 600, fontSize: 15 }}>{o.kind}</span>
              <span className="mono" style={{ marginLeft: 'auto', fontSize: 9, color: o.tag.includes('PRO') ? WF.accent : WF.ink3, fontWeight: 700, letterSpacing: 0.6, border: `1px solid ${o.tag.includes('PRO') ? WF.accent : WF.rule}`, padding: '2px 5px' }}>{o.tag}</span>
            </div>
            <div style={{ fontSize: 12, color: WF.ink3, marginTop: 6, lineHeight: 1.45 }}>{o.sub}</div>
            {o.best && <div className="mono" style={{ fontSize: 10, color: WF.accent, fontWeight: 700, marginTop: 8, letterSpacing: 0.5 }}>← RECOMMENDED · 14d Pro free</div>}
          </div>
        ))}
      </div>
      <div style={{ padding: '8px 16px 24px' }}>
        <WFCallout>Read-only sync via your brokerage's official OAuth. We never see your password and we cannot place trades.</WFCallout>
      </div>
    </WFScreen>
  );
}

// ────────────── Settings ──────────────
function Settings() {
  return (
    <WFScreen>
      <WFAppBar title="Settings" leading={<span className="mono">‹</span>} />
      <div style={{ padding: '14px 16px', borderBottom: `1px solid ${WF.rule}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 48, height: 48, border: `1.5px solid ${WF.ink}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: WF.mono, fontWeight: 700 }}>SK</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600 }}>sansar.k@example.com</div>
            <div style={{ fontSize: 12, color: WF.ink3, marginTop: 2 }}>Pro · trial day 9 of 14 <span style={{ color: WF.accent, fontWeight: 600 }}>· manage</span></div>
          </div>
        </div>
      </div>
      <SettingsGroup title="Daily digest">
        <SettingsRow label="Delivery time" value="7:00 AM ET" />
        <SettingsRow label="Length" value="Standard" />
        <SettingsRow label="Verbose mode" value="Pro · on" />
        <SettingsRow label="Digest alerts" value="On" toggle />
      </SettingsGroup>
      <SettingsGroup title="Alerts">
        <SettingsRow label="Grade changes" value="On" toggle />
        <SettingsRow label="Major news" value="On" toggle />
        <SettingsRow label="Portfolio grade" value="On" toggle />
        <SettingsRow label="Watchlist alerts" value="Pro · On" toggle />
        <SettingsRow label="Macro shock" value="Pro · On" toggle />
        <SettingsRow label="Severity threshold" value="AA→BBB or worse" />
      </SettingsGroup>
      <SettingsGroup title="Quiet hours">
        <SettingsRow label="Start" value="10:00 PM" />
        <SettingsRow label="End" value="7:00 AM" />
      </SettingsGroup>
      <SettingsGroup title="Data & privacy">
        <SettingsRow label="Methodology" value="v2.0 · read" />
        <SettingsRow label="Export portfolio" value="CSV ↗" />
        <SettingsRow label="Connected brokerage" value="Fidelity · Schwab" />
        <SettingsRow label="Delete account" value="" link />
      </SettingsGroup>
      <div style={{ padding: '16px 16px 24px' }}>
        <div className="mono" style={{ fontSize: 10, color: WF.ink4, textAlign: 'center', letterSpacing: 0.5 }}>Clavix · v1.0 · Andover Digital LLC</div>
      </div>
      <WFTabBar active="settings" />
    </WFScreen>
  );
}

function SettingsGroup({ title, children }) {
  return (
    <>
      <div style={{ padding: '20px 16px 6px' }}><WFEyebrow>{title}</WFEyebrow></div>
      <div style={{ borderTop: `1px solid ${WF.rule}` }}>{children}</div>
    </>
  );
}

function SettingsRow({ label, value, toggle, link }) {
  return (
    <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', borderBottom: `1px solid ${WF.rule2}` }}>
      <span style={{ flex: 1, fontSize: 14, color: link ? WF.bad : WF.ink }}>{label}</span>
      {toggle ? (
        <div style={{ width: 32, height: 18, border: `1px solid ${WF.ink}`, position: 'relative' }}>
          <div style={{ position: 'absolute', right: 1, top: 1, bottom: 1, width: 14, background: WF.ink }} />
        </div>
      ) : (
        <span className="mono" style={{ fontSize: 12, color: WF.ink3 }}>{value} ›</span>
      )}
    </div>
  );
}

// ────────────── Paywall ──────────────
function Paywall() {
  return (
    <WFScreen>
      <div style={{ padding: '14px 16px', display: 'flex', alignItems: 'center' }}>
        <span style={{ flex: 1 }} /><span className="mono" style={{ fontSize: 14, color: WF.ink3 }}>×</span>
      </div>
      <div style={{ padding: '20px 24px 12px' }}>
        <WFProBadge size={11} />
        <div style={{ fontSize: 30, fontWeight: 600, lineHeight: 1.15, letterSpacing: -0.5, marginTop: 14 }}>Unlock the full briefing.</div>
        <div style={{ fontSize: 14, color: WF.ink2, lineHeight: 1.5, marginTop: 10 }}>
          You're using Clavix Free. <b>Upgrade to Pro</b> to connect your brokerage, watch unlimited tickers, and get the verbose digest.
        </div>
      </div>
      <div style={{ margin: '14px 16px', padding: 16, border: `1.5px solid ${WF.ink}` }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
          <span className="mono" style={{ fontSize: 30, fontWeight: 700 }}>$20</span>
          <span style={{ fontSize: 13, color: WF.ink3 }}>/ month</span>
          <span className="mono" style={{ marginLeft: 'auto', fontSize: 10, color: WF.accent, fontWeight: 700, letterSpacing: 0.6 }}>14D FREE TRIAL</span>
        </div>
        <div style={{ fontSize: 11, color: WF.ink3, marginTop: 4 }}>No credit card required. Auto-downgrades to Free on day 15.</div>
      </div>
      <div style={{ padding: '8px 16px 6px' }}><WFEyebrow>Free → Pro</WFEyebrow></div>
      <table style={{ width: 'calc(100% - 32px)', margin: '0 16px', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: `1.5px solid ${WF.ink}` }}>
            <th style={{ textAlign: 'left', padding: 6 }}> </th>
            <th className="mono" style={{ textAlign: 'right', padding: 6, fontSize: 10, color: WF.ink3 }}>FREE</th>
            <th className="mono" style={{ textAlign: 'right', padding: 6, fontSize: 10, color: WF.accent }}>PRO</th>
          </tr>
        </thead>
        <tbody>
          {[
            ['Holdings', '3', '∞'],
            ['Watchlist', '5', '∞'],
            ['Brokerage sync', '—', '✓'],
            ['CSV import', '—', '✓'],
            ['Verbose digest', '—', '✓'],
            ['Manual refresh', '—', '5/day'],
            ['Watchlist alerts', '—', '✓'],
            ['Macro shock alerts', '—', '✓'],
            ['News window', '7d', '30d'],
          ].map(r => (
            <tr key={r[0]} style={{ borderBottom: `1px solid ${WF.rule2}` }}>
              <td style={{ padding: 6 }}>{r[0]}</td>
              <td className="mono" style={{ padding: 6, textAlign: 'right', color: WF.ink3 }}>{r[1]}</td>
              <td className="mono" style={{ padding: 6, textAlign: 'right', fontWeight: 700 }}>{r[2]}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ padding: '20px 16px 24px' }}>
        <button style={{ width: '100%', padding: '14px 0', background: WF.ink, color: '#fff', fontWeight: 600, fontSize: 15 }}>Start 14-day trial</button>
        <button style={{ marginTop: 10, fontSize: 12, color: WF.ink3, width: '100%' }}>Restore purchase · Terms · Privacy</button>
      </div>
    </WFScreen>
  );
}

Object.assign(window, {
  Portfolio, MethodologyDrawer, MethodologyAuditNews,
  MethodologyAuditFinHealth, MethodologyAuditMacro,
  MethodologyAuditSector, MethodologyAuditVolatility,
  ArticleDetail, Search, Alerts, OnboardA, OnboardB,
  Settings, Paywall, DistributionChart, ArticleTable,
  SettingsGroup, SettingsRow,
});
