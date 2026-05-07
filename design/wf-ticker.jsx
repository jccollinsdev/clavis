// wf-ticker.jsx — Ticker Detail screens
// C (Radar) is the chosen direction. Changes from v1:
//   - Remove 18d composite sparkline from hero
//   - Add stock chart placeholder BELOW hero card
//   - Remove "Fundamentals · last filing" section
//   - Add Executive Summary drawer (bullish / bearish / watch)
//   - Dimensions table tappable → opens methodology drill-down
//   - LLM reasoning hidden behind "Why this score?" toggle

const NVDA = {
  tkr: 'NVDA',
  name: 'NVIDIA Corporation',
  price: 942.18,
  dPrice: -1.42,
  dPct: -0.15,
  grade: 'A',
  score: 74,
  dimensions: [
    { name: 'Financial Health', abbrev: 'Fin Health', score: 84, sub: 'Strong: D/E 0.41 · FCF 41%' },
    { name: 'News Sentiment',   abbrev: 'News',       score: 58, sub: '12 articles · 7d · falling' },
    { name: 'Macro Exposure',   abbrev: 'Macro',      score: 68, sub: 'High beta · rate-sensitive' },
    { name: 'Sector Exposure',  abbrev: 'Sector',     score: 71, sub: 'Tech · momentum +' },
    { name: 'Volatility',       abbrev: 'Vol',        score: 89, sub: '30d 28% · falling' },
  ],
  scoreSpark: [82, 82, 81, 82, 81, 80, 80, 79, 79, 78, 78, 77, 77, 76, 75, 75, 74, 74],
};

const NEWS = [
  { src: 'Reuters',       tier: 1, ago: '3h',  sent: 32, head: 'EU widens NVIDIA antitrust probe to cover enterprise GPU supply contracts',       tag: 'regulatory' },
  { src: 'WSJ',           tier: 1, ago: '5h',  sent: 38, head: 'Cloud customers say NVIDIA contract terms are under review',                       tag: 'regulatory' },
  { src: 'Bloomberg',     tier: 1, ago: '7h',  sent: 41, head: 'NVIDIA: probe is "ordinary course" — no operational impact',                       tag: 'leadership' },
  { src: 'Seeking Alpha', tier: 2, ago: '12h', sent: 64, head: 'Q1 datacenter revenue still likely to print +$2B above consensus',                 tag: 'financial-impact' },
  { src: 'CNBC',          tier: 2, ago: '1d',  sent: 55, head: 'Analysts split on antitrust impact — some see negotiation, others see breakup risk', tag: 'sector' },
];

// ════════════════════════════════════════════════════════════════
//   A · Hero grade + bar chart of dimensions
// ════════════════════════════════════════════════════════════════
function TickerA() {
  return (
    <WFScreen>
      <WFAppBar title={NVDA.tkr} subtitle={NVDA.name.toUpperCase()} leading={<span className="mono" style={{ fontSize: 16 }}>‹</span>} trailing={<span className="mono" style={{ fontSize: 16 }}>↻</span>} />
      <div style={{ padding: '18px 16px 16px', borderBottom: `1px solid ${WF.rule}`, display: 'flex', gap: 14, alignItems: 'center' }}>
        <WFGrade grade={NVDA.grade} size="hero" />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <WFEyebrow>Composite</WFEyebrow>
          <div className="mono" style={{ fontSize: 32, fontWeight: 600, lineHeight: 1 }}>{NVDA.score}</div>
          <div className="mono" style={{ fontSize: 11, color: WF.ink3 }}>was 79 · ▼ 5</div>
        </div>
      </div>
      <div style={{ padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', borderBottom: `1px solid ${WF.rule2}` }}>
        <div>
          <span className="mono" style={{ fontSize: 22, fontWeight: 600 }}>${NVDA.price}</span>
          <span className="mono" style={{ fontSize: 13, color: WF.bad, marginLeft: 8 }}>▼ {Math.abs(NVDA.dPrice).toFixed(2)} ({NVDA.dPct}%)</span>
        </div>
        <span className="mono" style={{ fontSize: 11, color: WF.ink3 }}>last close</span>
      </div>
      <div style={{ padding: '20px 16px 8px' }}><WFEyebrow>Risk dimensions · tap any bar</WFEyebrow></div>
      <div style={{ padding: '0 16px', display: 'flex', gap: 6, alignItems: 'flex-end' }}>
        {NVDA.dimensions.map(d => <WFDimensionBar key={d.name} {...d} />)}
      </div>
      <div style={{ padding: '20px 16px 6px' }}><WFEyebrow>What's driving the grade</WFEyebrow></div>
      <div style={{ padding: '0 16px', fontSize: 14, lineHeight: 1.55, color: WF.ink2 }}>
        Three Tier-1 outlets reported on the widening EU probe. <b>News sentiment fell 71 → 58</b>, the largest contributor to the 5-point composite drop.
      </div>
      <div style={{ padding: '20px 16px 4px', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <WFEyebrow>Recent news · last 7d</WFEyebrow>
        <span className="mono" style={{ fontSize: 10, color: WF.ink3 }}>12 articles</span>
      </div>
      <div style={{ padding: '0 16px' }}>
        {NEWS.slice(0, 3).map(n => (
          <div key={n.head} style={{ padding: '12px 0', borderTop: `1px solid ${WF.rule2}` }}>
            <div className="mono" style={{ fontSize: 10, color: WF.ink3, display: 'flex', gap: 8 }}>
              <span>{n.src} · T{n.tier}</span><span>{n.ago} ago</span>
              <span style={{ marginLeft: 'auto', fontWeight: 700, color: n.sent < 50 ? WF.bad : WF.ink2 }}>sent {n.sent}</span>
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.4, marginTop: 4 }}>{n.head}</div>
          </div>
        ))}
      </div>
      <div style={{ padding: '20px 16px 24px', display: 'flex', gap: 8 }}>
        <button style={{ flex: 1, padding: '12px 0', border: `1.5px solid ${WF.ink}`, fontSize: 13, fontWeight: 600 }}>+ Holdings</button>
        <button style={{ flex: 1, padding: '12px 0', border: `1px solid ${WF.rule}`, fontSize: 13 }}>+ Watchlist</button>
      </div>
      <WFTabBar active="search" />
    </WFScreen>
  );
}

// ════════════════════════════════════════════════════════════════
//   B · Pills row
// ════════════════════════════════════════════════════════════════
function TickerB() {
  return (
    <WFScreen>
      <WFAppBar title="NVDA" leading={<span className="mono" style={{ fontSize: 16 }}>‹</span>} trailing={<span className="mono" style={{ fontSize: 14 }}>★</span>} />
      <div style={{ padding: '14px 16px 8px' }}>
        <div style={{ fontSize: 14, color: WF.ink3 }}>{NVDA.name}</div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginTop: 2 }}>
          <span className="mono" style={{ fontSize: 36, fontWeight: 600, letterSpacing: -0.5 }}>${NVDA.price}</span>
          <span className="mono" style={{ fontSize: 13, color: WF.bad }}>▼ {Math.abs(NVDA.dPrice).toFixed(2)} ({NVDA.dPct}%)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8 }}>
          <WFGrade grade={NVDA.grade} size="sm" delta={-1} />
          <span className="mono" style={{ fontSize: 12, color: WF.ink2 }}>{NVDA.score}/100</span>
          <span style={{ fontSize: 12, color: WF.ink3 }}>· down 5</span>
        </div>
      </div>
      <div style={{ padding: '8px 16px 12px' }}>
        <WFBox height={130} label="[ price chart · 30d ]" />
      </div>
      <div style={{ padding: '8px 16px 6px' }}><WFEyebrow>Risk dimensions</WFEyebrow></div>
      <div style={{ padding: '0 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {NVDA.dimensions.map(d => (
          <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', border: `1px solid ${WF.rule}` }}>
            <span style={{ flex: 1, fontSize: 13, fontWeight: 500 }}>{d.name}</span>
            <span className="mono" style={{ fontSize: 11, color: WF.ink3, width: 110 }}>{d.sub}</span>
            <div style={{ width: 56 }}><WFScoreBar score={d.score} height={4} /></div>
            <span className="mono" style={{ fontSize: 13, fontWeight: 700, width: 28, textAlign: 'right' }}>{d.score}</span>
          </div>
        ))}
      </div>
      <div style={{ padding: '20px 16px 6px' }}><WFEyebrow>Recent news</WFEyebrow></div>
      <div style={{ padding: '0 16px' }}>
        {NEWS.slice(0, 4).map(n => (
          <div key={n.head} style={{ padding: '10px 0', borderTop: `1px solid ${WF.rule2}`, display: 'flex', gap: 10 }}>
            <div className="mono" style={{ fontSize: 11, color: n.sent < 50 ? WF.bad : WF.ink2, width: 28, textAlign: 'right', fontWeight: 700 }}>{n.sent}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12, lineHeight: 1.35 }}>{n.head}</div>
              <div className="mono" style={{ fontSize: 10, color: WF.ink3, marginTop: 2 }}>{n.src} · {n.ago}</div>
            </div>
          </div>
        ))}
      </div>
      <div style={{ padding: '20px 16px 24px' }}>
        <button style={{ width: '100%', padding: '14px 0', background: WF.ink, color: '#fff', fontSize: 14, fontWeight: 600 }}>Add to portfolio</button>
      </div>
      <WFTabBar active="search" />
    </WFScreen>
  );
}

// ════════════════════════════════════════════════════════════════
//   Radar primitive (shared by C and exec summary)
// ════════════════════════════════════════════════════════════════
function RadarChart({ values, size = 200 }) {
  const cx = size / 2, cy = size / 2;
  const r = size / 2 - 22;
  const n = values.length;
  const angle = (i) => (Math.PI * 2 * i) / n - Math.PI / 2;
  const point = (i, v) => {
    const rr = (v / 100) * r;
    return [cx + Math.cos(angle(i)) * rr, cy + Math.sin(angle(i)) * rr];
  };
  const rings = [20, 40, 60, 80, 100].map(p => p / 100);
  return (
    <svg width={size} height={size}>
      {rings.map((p, idx) => {
        const pts = values.map((_, i) => {
          const rr = p * r;
          return `${cx + Math.cos(angle(i)) * rr},${cy + Math.sin(angle(i)) * rr}`;
        }).join(' ');
        return <polygon key={idx} points={pts} fill="none" stroke={WF.rule} strokeWidth="0.5" />;
      })}
      {values.map((_, i) => {
        const [x, y] = [cx + Math.cos(angle(i)) * r, cy + Math.sin(angle(i)) * r];
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke={WF.rule2} strokeWidth="0.5" />;
      })}
      <polygon
        points={values.map((v, i) => point(i, v.score).join(',')).join(' ')}
        fill="#00000018" stroke={WF.ink} strokeWidth="1.5"
      />
      {values.map((v, i) => {
        const [x, y] = point(i, v.score);
        return <circle key={i} cx={x} cy={y} r="3" fill={WF.ink} />;
      })}
      {values.map((v, i) => {
        const [x, y] = [cx + Math.cos(angle(i)) * (r + 14), cy + Math.sin(angle(i)) * (r + 14)];
        return <text key={i} x={x} y={y} fontSize="9" fontFamily={WF.mono} fill={WF.ink3} textAnchor="middle" dominantBaseline="middle">{v.abbrev}</text>;
      })}
    </svg>
  );
}

// ════════════════════════════════════════════════════════════════
//   C · Radar + table — CHOSEN DIRECTION
//   Changes: no 18d sparkline, stock chart below hero,
//   exec summary tap, no fundamentals, "Why this score?" toggle
// ════════════════════════════════════════════════════════════════
function TickerC() {
  const { useState } = React;
  const [showExecSummary, setShowExecSummary] = useState(false);
  const [whyOpenIdx, setWhyOpenIdx] = useState(null);

  return (
    <WFScreen scroll={!showExecSummary}>
      <WFAppBar
        title="NVDA · Risk"
        leading={<span className="mono">‹</span>}
        trailing={
          <button
            onClick={() => setShowExecSummary(true)}
            style={{ fontFamily: WF.mono, fontSize: 10, fontWeight: 700, color: WF.accent, letterSpacing: 0.4, padding: '3px 6px', border: `1px solid ${WF.accent}` }}
          >SUMMARY</button>
        }
      />

      {/* ── HERO CARD: radar + grade + score ── */}
      <div style={{ padding: '14px 16px 12px', display: 'flex', gap: 8, alignItems: 'flex-start', borderBottom: `1px solid ${WF.rule}` }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <WFGrade grade={NVDA.grade} size="lg" delta={-1} />
          <div className="mono" style={{ fontSize: 22, fontWeight: 600 }}>{NVDA.score}/100</div>
          <div className="mono" style={{ fontSize: 10, color: WF.ink3 }}>NVIDIA · ${NVDA.price} · ▼ 0.15%</div>
          <div className="mono" style={{ fontSize: 10, color: WF.ink3 }}>was 79 · ▼ 5</div>
        </div>
        <div style={{ flexShrink: 0 }}>
          <RadarChart values={NVDA.dimensions} size={170} />
        </div>
      </div>

      {/* ── STOCK CHART — below hero, above dimensions ── */}
      <div style={{ padding: '14px 16px 4px' }}>
        <WFEyebrow>Price · 30d</WFEyebrow>
      </div>
      <div style={{ padding: '0 16px 4px' }}>
        <WFBox height={110} label="[ price chart · 30d candles ]" />
        <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
          {['1D', '5D', '1M', '3M', 'YTD', '1Y'].map(p => (
            <div key={p} style={{ flex: 1, padding: '4px 0', textAlign: 'center', fontSize: 10, fontFamily: WF.mono, border: `1px solid ${p === '1M' ? WF.ink : WF.rule}`, fontWeight: p === '1M' ? 700 : 400 }}>{p}</div>
          ))}
        </div>
      </div>

      {/* ── DIMENSIONS TABLE ── */}
      <div style={{ padding: '14px 16px 4px' }}><WFEyebrow>Dimensions · tap row for full audit</WFEyebrow></div>
      <table style={{ width: 'calc(100% - 32px)', margin: '0 16px', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: `1.5px solid ${WF.ink}` }}>
            <th style={{ textAlign: 'left', padding: '6px 4px', fontFamily: WF.mono, fontSize: 9, color: WF.ink3, fontWeight: 600, letterSpacing: 0.6 }}>DIMENSION</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', fontFamily: WF.mono, fontSize: 9, color: WF.ink3, fontWeight: 600 }}>SCORE</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', fontFamily: WF.mono, fontSize: 9, color: WF.ink3, fontWeight: 600 }}>Δ7D</th>
            <th style={{ textAlign: 'right', padding: '6px 4px', fontFamily: WF.mono, fontSize: 9, color: WF.ink3, fontWeight: 600 }}>UPDATED</th>
            <th style={{ width: 16 }}></th>
          </tr>
        </thead>
        <tbody>
          {NVDA.dimensions.map((d, i) => {
            const deltas = [+1, -13, 0, 0, +2];
            const updated = ['Q1 25', '3h', '12h', '6h', 'EOD'];
            return (
              <tr key={d.name} style={{ borderBottom: `1px solid ${WF.rule2}`, cursor: 'pointer' }}>
                <td style={{ padding: '8px 4px' }}>{d.name}</td>
                <td className="mono" style={{ padding: '8px 4px', textAlign: 'right', fontWeight: 700 }}>{d.score}</td>
                <td className="mono" style={{ padding: '8px 4px', textAlign: 'right', color: deltas[i] === 0 ? WF.ink3 : (deltas[i] > 0 ? WF.good : WF.bad) }}>
                  {deltas[i] === 0 ? '—' : (deltas[i] > 0 ? '+' : '') + deltas[i]}
                </td>
                <td className="mono" style={{ padding: '8px 4px', textAlign: 'right', color: WF.ink3 }}>{updated[i]}</td>
                <td className="mono" style={{ padding: '8px 4px', textAlign: 'right', color: WF.ink3, fontSize: 10 }}>›</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div style={{ padding: '4px 16px 4px' }}>
        <WFCallout>Tap any dimension row to open the full methodology audit for that score.</WFCallout>
      </div>

      {/* ── NEWS ── */}
      <div style={{ padding: '18px 16px 6px' }}><WFEyebrow>News · 12 articles · 7d</WFEyebrow></div>
      <div style={{ padding: '0 16px' }}>
        {NEWS.slice(0, 4).map((n, ni) => (
          <div key={n.head} style={{ padding: '10px 0', borderTop: `1px solid ${WF.rule2}` }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
              <span className="mono" style={{ fontSize: 11, color: n.sent < 50 ? WF.bad : WF.ink, fontWeight: 700, width: 24 }}>{n.sent}</span>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: 12, lineHeight: 1.35 }}>{n.head}</span>
                <div className="mono" style={{ fontSize: 10, color: WF.ink3, marginTop: 2 }}>{n.src} · T{n.tier} · {n.ago}</div>
              </div>
              <span className="mono" style={{ fontSize: 10, color: WF.ink3 }}>›</span>
            </div>

            {/* "Why this score?" toggle */}
            <button
              onClick={() => setWhyOpenIdx(whyOpenIdx === ni ? null : ni)}
              style={{ marginTop: 6, fontSize: 10, color: WF.ink3, fontFamily: WF.mono, display: 'flex', alignItems: 'center', gap: 4 }}
            >
              <span style={{ fontSize: 9 }}>{whyOpenIdx === ni ? '▲' : '▼'}</span>
              Why this score?
            </button>
            {whyOpenIdx === ni && (
              <div style={{ marginTop: 6, padding: '8px 10px', background: WF.paper2, border: `1px dashed ${WF.rule}`, fontSize: 11, color: WF.ink3, lineHeight: 1.5, fontFamily: WF.mono }}>
                {ni === 0 ? 'Regulatory escalation framing. Direct revenue tie. T1 source weight upgrades signal credibility. No softening hedge in body. Compares to recent large-cap tech regulatory escalations (median ~30).' :
                 ni === 1 ? 'Contract review language implies enforced renegotiation risk. T1 source. Incremental negative over prior probe story.' :
                 ni === 2 ? '"Ordinary course" softens the headline. Official denial from company. Still below neutral — denial doesn\'t erase the escalation signal.' :
                 'Buy-side analyst note. T2 weighting. Bullish framing offsets regulatory drag partially.'}
              </div>
            )}
          </div>
        ))}
        <button style={{ padding: '10px 0', fontSize: 12, color: WF.ink3, fontFamily: WF.mono }}>+ 8 more articles ›</button>
      </div>

      <div style={{ height: 24 }} />
      <WFTabBar active="search" />

      {/* ── EXECUTIVE SUMMARY DRAWER ── */}
      {showExecSummary && (
        <div style={{
          position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.35)',
          display: 'flex', flexDirection: 'column', justifyContent: 'flex-end',
        }} onClick={() => setShowExecSummary(false)}>
          <div
            onClick={e => e.stopPropagation()}
            style={{
              background: WF.paper, borderTop: `2px solid ${WF.ink}`,
              padding: '16px 16px 32px', maxHeight: '72%', overflow: 'auto',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 14 }}>
              <div style={{ flex: 1 }}>
                <WFEyebrow>Executive Summary · NVDA</WFEyebrow>
                <div style={{ fontSize: 16, fontWeight: 600, marginTop: 3 }}>Risk snapshot</div>
              </div>
              <button onClick={() => setShowExecSummary(false)} className="mono" style={{ fontSize: 16, color: WF.ink3 }}>×</button>
            </div>

            {/* BULLISH TAILWINDS */}
            <div style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <div style={{ width: 8, height: 8, background: WF.good }} />
                <WFEyebrow style={{ color: WF.good }}>Bullish tailwinds</WFEyebrow>
              </div>
              {[
                'Financial health is strong — D/E 0.41, FCF margin 41%, interest coverage 38×',
                'Volatility score 89 — 30d realized vol falling, options market calm',
                'Sector momentum positive — Tech sector up +0.4% overnight',
                'Q1 datacenter revenue tracking +$2B above consensus (Seeking Alpha T2)',
              ].map((pt, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, padding: '5px 0', borderTop: `1px solid ${WF.rule2}`, fontSize: 13, color: WF.ink2, lineHeight: 1.4 }}>
                  <span style={{ color: WF.good, fontWeight: 700, flexShrink: 0 }}>+</span>
                  <span>{pt}</span>
                </div>
              ))}
            </div>

            {/* BEARISH HEADWINDS */}
            <div style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <div style={{ width: 8, height: 8, background: WF.bad }} />
                <WFEyebrow style={{ color: WF.bad }}>Bearish headwinds</WFEyebrow>
              </div>
              {[
                'EU antitrust probe expanded to enterprise GPU supply contracts — 3 Tier-1 articles',
                'News sentiment collapsed 71 → 58, largest single-dimension drop',
                'Grade downgraded AA → A — portfolio composite down 5 points',
                'High macro beta — rate sensitive, CPI revision today is a live risk',
              ].map((pt, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, padding: '5px 0', borderTop: `1px solid ${WF.rule2}`, fontSize: 13, color: WF.ink2, lineHeight: 1.4 }}>
                  <span style={{ color: WF.bad, fontWeight: 700, flexShrink: 0 }}>−</span>
                  <span>{pt}</span>
                </div>
              ))}
            </div>

            {/* WHAT TO LOOK FOR */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <div style={{ width: 8, height: 8, background: WF.ink, transform: 'rotate(45deg)' }} />
                <WFEyebrow>What to look for</WFEyebrow>
              </div>
              {[
                'EU phase-1 review timeline: typically 25 working days to preliminary finding',
                'Watch for further T1 coverage — volume is 2.4× 4-week average, elevated',
                'CPI at 08:30 ET — any hawkish surprise increases NVDA\'s rate sensitivity drag',
                'Q1 earnings date: any pre-announcement or guidance revision changes the picture',
              ].map((pt, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, padding: '5px 0', borderTop: `1px solid ${WF.rule2}`, fontSize: 13, color: WF.ink2, lineHeight: 1.4 }}>
                  <span className="mono" style={{ color: WF.ink3, flexShrink: 0 }}>→</span>
                  <span>{pt}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </WFScreen>
  );
}

// ════════════════════════════════════════════════════════════════
//   D · Terminal-style (kept from v1, minor clean)
// ════════════════════════════════════════════════════════════════
function TickerD() {
  return (
    <WFScreen bg="#fafaf8">
      <div style={{ padding: '12px 16px 6px', borderBottom: `1px solid ${WF.ink}`, display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span className="mono" style={{ fontSize: 22, fontWeight: 700 }}>NVDA</span>
        <span style={{ fontSize: 11, color: WF.ink3 }}>NVIDIA</span>
        <span className="mono" style={{ marginLeft: 'auto', fontSize: 11, color: WF.ink3 }}>‹ back</span>
      </div>
      <div className="mono" style={{ background: WF.ink, color: '#fff', padding: '14px 16px', fontSize: 12, lineHeight: 1.7 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: '#a8b0bf' }}>GRADE</span>
          <span style={{ fontSize: 22, fontWeight: 700 }}>A <span style={{ color: WF.bad, fontSize: 12 }}>▼1</span></span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: '#a8b0bf' }}>SCORE</span>
          <span>74 <span style={{ color: '#a8b0bf' }}>was 79</span></span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: '#a8b0bf' }}>PRICE</span>
          <span>$942.18 <span style={{ color: WF.bad }}>−0.15%</span></span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: '#a8b0bf' }}>UPDATED</span>
          <span>06 May 06:58 ET</span>
        </div>
      </div>
      <div style={{ padding: '14px 16px 4px' }}><WFEyebrow>5 dimensions</WFEyebrow></div>
      <div style={{ padding: '0 16px' }}>
        {NVDA.dimensions.map((d, i) => {
          const deltas = ['  +1', ' −13', '   0', '   0', '  +2'];
          return (
            <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 0', borderTop: `1px solid ${WF.rule2}` }}>
              <span className="mono" style={{ width: 26, fontSize: 11, color: WF.ink3 }}>0{i + 1}</span>
              <span style={{ flex: 1, fontSize: 13 }}>{d.name}</span>
              <span className="mono" style={{ fontSize: 14, fontWeight: 700, width: 32, textAlign: 'right' }}>{d.score}</span>
              <span className="mono" style={{ fontSize: 11, color: deltas[i].includes('−') ? WF.bad : WF.ink3, width: 38, textAlign: 'right', whiteSpace: 'pre' }}>{deltas[i]}</span>
              <span className="mono" style={{ width: 14, textAlign: 'right', color: WF.ink4 }}>›</span>
            </div>
          );
        })}
      </div>
      <div style={{ padding: '14px 16px 4px' }}><WFEyebrow>News · 7d · sentiment scored</WFEyebrow></div>
      <div className="mono" style={{ padding: '0 16px', fontSize: 11, lineHeight: 1.5 }}>
        {NEWS.map(n => (
          <div key={n.head} style={{ padding: '6px 0', borderTop: `1px solid ${WF.rule2}`, display: 'flex', gap: 6 }}>
            <span style={{ width: 24, color: n.sent < 50 ? WF.bad : WF.ink2, fontWeight: 700 }}>{n.sent}</span>
            <span style={{ width: 32, color: WF.ink3 }}>{n.ago}</span>
            <span style={{ width: 36, color: WF.ink3 }}>T{n.tier}</span>
            <span style={{ flex: 1, color: WF.ink, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{n.head}</span>
          </div>
        ))}
      </div>
      <div style={{ height: 24 }} />
      <WFTabBar active="search" />
    </WFScreen>
  );
}

Object.assign(window, { TickerA, TickerB, TickerC, TickerD, RadarChart });
