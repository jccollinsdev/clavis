// wf-digest.jsx — Daily Digest screens
// D now has 3 concept variations (D1, D2, D3) all structured:
//   macro overview (text) → sector overview (text) → positions (diff-led)

const DIGEST_DATE = 'Wed · May 6, 2026 · 7:02 AM ET';
const PORTFOLIO_GRADE = 'AA';
const PORTFOLIO_SCORE = 81;
const PORTFOLIO_DELTA = -1;

const POSITIONS = [
  { tkr: 'NVDA', name: 'NVIDIA Corp',          grade: 'A',   score: 74, dGrade: -1, weight: '8.2%', headline: 'Antitrust probe widens to enterprise GPU contracts; news sentiment fell from 71 to 58.', impact: 'high' },
  { tkr: 'XOM',  name: 'Exxon Mobil',          grade: 'AA',  score: 82, dGrade: 0,  weight: '5.4%', headline: 'Crude up 1.8% overnight on OPEC+ headlines; macro exposure unchanged.', impact: 'med' },
  { tkr: 'AAPL', name: 'Apple Inc.',           grade: 'AAA', score: 91, dGrade: 0,  weight: '11.4%', headline: 'No material news. Sector backdrop steady.', impact: 'low' },
  { tkr: 'MSFT', name: 'Microsoft',            grade: 'AAA', score: 90, dGrade: 0,  weight: '9.1%',  headline: 'No material news.', impact: 'low' },
  { tkr: 'JPM',  name: 'JPMorgan Chase',       grade: 'AA',  score: 84, dGrade: 0,  weight: '4.8%',  headline: 'No material news. Fed minutes at 2pm ET — watch.', impact: 'low' },
  { tkr: 'VOO',  name: 'Vanguard S&P 500 ETF', grade: 'AAA', score: 93, dGrade: 0,  weight: '22.0%', headline: 'No material news.', impact: 'low' },
  { tkr: 'TLT',  name: '20+ Year Treasury ETF',grade: 'AA',  score: 80, dGrade: +1, weight: '6.0%',  headline: '10Y yield drifted 4bp lower; TLT ticked up.', impact: 'low' },
];

const MACRO_TEXT = `S&P futures +0.18% after soft Asia session. 10Y yield at 4.31% — drifted 4bp lower overnight. Crude +1.8% on OPEC+ rollover talk. Dollar slipped on CPI revision speculation. No macro shocks. CPI revision 08:30 ET and Fed minutes 14:00 ET are the day's risk windows.`;

const SECTOR_ROWS = [
  { name: 'Technology',  ch: '+0.4%', dir: 1,  holds: 'AAPL · MSFT · NVDA', note: 'NVDA is the drag; AAPL/MSFT quiet' },
  { name: 'Energy',      ch: '+1.1%', dir: 1,  holds: 'XOM',                 note: 'OPEC+ tailwind, sector best overnight' },
  { name: 'Financials',  ch: '−0.1%', dir: -1, holds: 'JPM',                 note: 'Flat; Fed minutes at 14:00 ET' },
  { name: 'Treasuries',  ch: '+0.3%', dir: 1,  holds: 'TLT',                 note: '10Y yield down; TLT score +1' },
];

// ════════════════════════════════════════════════════════════════
//   A · Prose-led briefing (kept from v1)
// ════════════════════════════════════════════════════════════════
function DigestA() {
  return (
    <WFScreen>
      <div style={{ padding: '14px 16px 8px' }}>
        <WFEyebrow>Daily Briefing</WFEyebrow>
        <div style={{ fontSize: 11, color: WF.ink3, marginTop: 4 }}>{DIGEST_DATE}</div>
      </div>
      <div style={{ padding: '8px 16px 16px', display: 'flex', alignItems: 'center', gap: 16, borderBottom: `1px solid ${WF.rule}` }}>
        <WFGrade grade={PORTFOLIO_GRADE} size="hero" />
        <div style={{ flex: 1 }}>
          <div className="mono" style={{ fontSize: 10, color: WF.ink3, letterSpacing: 0.6, textTransform: 'uppercase' }}>Portfolio rating</div>
          <div className="mono" style={{ fontSize: 28, fontWeight: 600, marginTop: 2 }}>{PORTFOLIO_SCORE}<span style={{ fontSize: 14, color: WF.ink3 }}>/100</span></div>
          <div style={{ fontSize: 12, color: WF.ink2, marginTop: 4 }}>Down <b>1 pt</b> from yesterday. <span style={{ color: WF.ink3 }}>Driven by NVDA news.</span></div>
        </div>
      </div>
      <div style={{ padding: '18px 16px 6px' }}><WFEyebrow>§ Overnight Macro</WFEyebrow></div>
      <div style={{ padding: '0 16px', fontSize: 14, lineHeight: 1.55, color: WF.ink2 }}>
        S&P futures <span className="mono">+0.18%</span> after Asia softness. 10Y at <span className="mono">4.31%</span>. Crude up on OPEC+. <b>CPI revision 8:30 ET, Fed minutes 2:00 PM ET</b> are the day's binary risk windows.
      </div>
      <div style={{ padding: '20px 16px 6px' }}><WFEyebrow>§ Sector Heat <span style={{ color: WF.ink4 }}>· yours</span></WFEyebrow></div>
      <div style={{ padding: '0 16px' }}>
        {SECTOR_ROWS.map(s => (
          <div key={s.name} style={{ display: 'flex', alignItems: 'baseline', padding: '6px 0', borderTop: `1px solid ${WF.rule2}`, fontSize: 13 }}>
            <span style={{ flex: 1 }}>{s.name}</span>
            <span className="mono" style={{ color: s.dir > 0 ? WF.good : WF.bad, marginRight: 12, fontWeight: 600 }}>{s.ch}</span>
            <span className="mono" style={{ fontSize: 10, color: WF.ink4 }}>{s.holds}</span>
          </div>
        ))}
      </div>
      <div style={{ padding: '22px 16px 6px' }}><WFEyebrow>§ Your Positions</WFEyebrow></div>
      <div style={{ padding: '0 16px 8px' }}>
        {POSITIONS.slice(0, 4).map((p, i) => (
          <div key={p.tkr} style={{ padding: '12px 0', borderTop: i === 0 ? 'none' : `1px solid ${WF.rule2}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <WFGrade grade={p.grade} size="sm" delta={p.dGrade} />
              <div style={{ flex: 1 }}>
                <span className="mono" style={{ fontSize: 13, fontWeight: 700 }}>{p.tkr}</span>
                <span style={{ fontSize: 11, color: WF.ink3, marginLeft: 6 }}>{p.name} · {p.weight} of book</span>
              </div>
              <span className="mono" style={{ fontSize: 11, color: WF.ink4 }}>›</span>
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.45, color: WF.ink2, marginTop: 6 }}>{p.headline}</div>
          </div>
        ))}
        <div style={{ paddingTop: 8, fontSize: 12, color: WF.ink3 }}>3 quieter holdings collapsed — tap to expand</div>
      </div>
      <WFTabBar active="digest" />
    </WFScreen>
  );
}

// ════════════════════════════════════════════════════════════════
//   B · Card stack (kept from v1)
// ════════════════════════════════════════════════════════════════
function DigestB() {
  return (
    <WFScreen bg={WF.paper2}>
      <WFAppBar title="Today" subtitle="MAY 6 · 7:02 AM" leading={<span className="mono" style={{ fontSize: 16 }}>≡</span>} trailing={<span className="mono" style={{ fontSize: 16 }}>◯</span>} />
      <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ background: WF.paper, border: `1px solid ${WF.rule}`, padding: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <WFGrade grade={PORTFOLIO_GRADE} size="lg" />
            <div style={{ flex: 1 }}>
              <WFEyebrow>Portfolio · 7 positions</WFEyebrow>
              <div className="mono" style={{ fontSize: 22, fontWeight: 600, marginTop: 2 }}>{PORTFOLIO_SCORE}<span style={{ fontSize: 12, color: WF.ink3 }}>/100  ▼ 1</span></div>
            </div>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6 }}>
          {[['ES1', '+0.18%', WF.good],['10Y', '4.31%', WF.ink],['DXY', '−0.2%', WF.bad],['VIX', '14.8', WF.ink]].map(([k, v, c]) => (
            <div key={k} style={{ background: WF.paper, border: `1px solid ${WF.rule}`, padding: '8px 6px' }}>
              <div className="mono" style={{ fontSize: 9, color: WF.ink3 }}>{k}</div>
              <div className="mono" style={{ fontSize: 14, fontWeight: 600, color: c, marginTop: 2 }}>{v}</div>
            </div>
          ))}
        </div>
        <div style={{ background: WF.paper, border: `1px solid ${WF.rule}`, padding: 12 }}>
          <WFEyebrow style={{ marginBottom: 8 }}>Sector · your holdings</WFEyebrow>
          {SECTOR_ROWS.map(s => (
            <div key={s.name} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', borderTop: `1px solid ${WF.rule2}`, fontSize: 12 }}>
              <span style={{ flex: 1 }}>{s.name}</span>
              <span className="mono" style={{ color: s.dir > 0 ? WF.good : WF.bad, fontWeight: 600 }}>{s.ch}</span>
            </div>
          ))}
        </div>
        <div style={{ padding: '4px 2px 2px' }}><WFEyebrow>Positions · ranked by change</WFEyebrow></div>
        {POSITIONS.map(p => (
          <div key={p.tkr} style={{ background: WF.paper, border: `1px solid ${WF.rule}`, padding: 12, borderLeft: p.impact === 'high' ? `3px solid ${WF.accent}` : `1px solid ${WF.rule}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <WFGrade grade={p.grade} size="sm" delta={p.dGrade} />
              <span className="mono" style={{ fontSize: 14, fontWeight: 700, flex: 1 }}>{p.tkr}</span>
              <span className="mono" style={{ fontSize: 11, color: WF.ink3 }}>{p.weight} · {p.score}</span>
            </div>
            {p.impact !== 'low' && <div style={{ fontSize: 12, color: WF.ink2, marginTop: 6, lineHeight: 1.4 }}>{p.headline}</div>}
            {p.impact === 'low' && <div className="mono" style={{ fontSize: 10, color: WF.ink4, marginTop: 4 }}>· quiet</div>}
          </div>
        ))}
      </div>
      <WFTabBar active="digest" />
    </WFScreen>
  );
}

// ════════════════════════════════════════════════════════════════
//   C · Hybrid (kept from v1)
// ════════════════════════════════════════════════════════════════
function DigestC() {
  return (
    <WFScreen>
      <div style={{ padding: '12px 16px 4px', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <WFEyebrow>WED · MAY 6 · 7:02 AM</WFEyebrow>
        <span className="mono" style={{ fontSize: 11, color: WF.ink3 }}>standard · 800w</span>
      </div>
      <div style={{ padding: '4px 16px 14px', fontSize: 22, fontWeight: 600, lineHeight: 1.2, letterSpacing: -0.3 }}>
        Quiet morning. <span style={{ color: WF.ink3 }}>One position moved — </span><span className="mono" style={{ color: WF.accent }}>NVDA</span><span style={{ color: WF.ink3 }}>.</span>
      </div>
      <div style={{ margin: '0 16px', padding: '12px 14px', border: `1px solid ${WF.ink}`, display: 'flex', alignItems: 'center', gap: 12 }}>
        <WFGrade grade={PORTFOLIO_GRADE} size="md" />
        <div style={{ flex: 1 }}>
          <span style={{ fontSize: 12, color: WF.ink2 }}>Portfolio · 7 positions</span>
          <span className="mono" style={{ display: 'block', fontSize: 11, color: WF.ink3, marginTop: 1 }}>{PORTFOLIO_SCORE}/100  ▼ 1 from yesterday</span>
        </div>
      </div>
      <div style={{ padding: '20px 16px 4px' }}><WFEyebrow>1 · Overnight Macro</WFEyebrow></div>
      <div style={{ padding: '0 16px', fontSize: 14, lineHeight: 1.55, color: WF.ink2 }}>
        S&P futures <span className="mono">+0.18%</span> after Asia softness. 10Y at <span className="mono">4.31%</span>. Crude up on OPEC+. <b>CPI revision 8:30, Fed minutes 14:00.</b>
      </div>
      <div style={{ padding: '18px 16px 4px' }}><WFEyebrow>2 · Sector backdrop · your sectors</WFEyebrow></div>
      <div style={{ padding: '0 16px', fontSize: 13, color: WF.ink2, lineHeight: 1.6 }}>
        <b>Tech +0.4%</b> — NVDA drag offsets AAPL/MSFT strength. <b>Energy +1.1%</b> on OPEC+, XOM is your biggest beneficiary. <b>Financials −0.1%</b>, JPM flat pre-Fed mins.
      </div>
      <div style={{ padding: '20px 16px 4px', display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
        <WFEyebrow>3 · Your Positions</WFEyebrow>
        <span className="mono" style={{ fontSize: 10, color: WF.ink3 }}>movers ↑ · quiet collapsed</span>
      </div>
      <div style={{ padding: '0 16px' }}>
        {POSITIONS.filter(p => p.impact !== 'low').map((p, i) => (
          <div key={p.tkr} style={{ padding: '12px 0', borderTop: `1px solid ${i === 0 ? WF.ink : WF.rule2}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <WFGrade grade={p.grade} size="sm" delta={p.dGrade} />
              <span className="mono" style={{ fontSize: 13, fontWeight: 700, flex: 1 }}>{p.tkr}</span>
              <span className="mono" style={{ fontSize: 11, color: WF.ink3 }}>{p.weight} · {p.score}</span>
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.45, color: WF.ink2, marginTop: 6 }}>{p.headline}</div>
          </div>
        ))}
        <button style={{ marginTop: 4, padding: '10px 0', textAlign: 'left', fontSize: 12, color: WF.ink3, display: 'flex', justifyContent: 'space-between', width: '100%' }}>
          <span>+ 5 quiet positions · AAPL MSFT JPM VOO TLT</span>
          <span className="mono">expand ▾</span>
        </button>
      </div>
      <WFTabBar active="digest" />
    </WFScreen>
  );
}

// ════════════════════════════════════════════════════════════════
//   D1 · Sectioned memo — editorial headings, inline diffs
//   Structure: macro (prose) → sector (prose) → positions (diff rows)
// ════════════════════════════════════════════════════════════════
function DigestD1() {
  return (
    <WFScreen>
      <div style={{ padding: '12px 16px 10px', display: 'flex', alignItems: 'center', gap: 10, borderBottom: `2px solid ${WF.ink}` }}>
        <div style={{ flex: 1 }}>
          <WFEyebrow>Daily Briefing · May 6</WFEyebrow>
          <div style={{ fontSize: 20, fontWeight: 600, lineHeight: 1.2, marginTop: 4, letterSpacing: -0.2 }}>
            1 move. Macro quiet. <span className="mono" style={{ color: WF.accent }}>NVDA</span> the story.
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <WFGrade grade="AA" size="md" delta={0} />
          <div className="mono" style={{ fontSize: 10, color: WF.ink3, marginTop: 4 }}>81 ▼ 1</div>
        </div>
      </div>

      {/* MACRO */}
      <div style={{ padding: '16px 16px 6px', display: 'flex', alignItems: 'center', gap: 8 }}>
        <WFEyebrow>Macro</WFEyebrow>
        <div style={{ flex: 1, height: 1, background: WF.rule2 }} />
        <span className="mono" style={{ fontSize: 9, color: WF.ink4 }}>NO CHANGE</span>
      </div>
      <div style={{ padding: '0 16px', fontSize: 13, lineHeight: 1.6, color: WF.ink2 }}>
        Futures <span className="mono">+0.18%</span>. 10Y yield <span className="mono">4.31%</span>, down 4bp. Crude <span className="mono">+1.8%</span> on OPEC+ rollover. Dollar soft. <b>CPI 08:30, Fed mins 14:00 ET</b> — watch these.
      </div>

      {/* SECTOR */}
      <div style={{ padding: '16px 16px 6px', display: 'flex', alignItems: 'center', gap: 8 }}>
        <WFEyebrow>Sector · your book</WFEyebrow>
        <div style={{ flex: 1, height: 1, background: WF.rule2 }} />
        <span className="mono" style={{ fontSize: 9, color: WF.ink4 }}>4 SECTORS</span>
      </div>
      <div style={{ padding: '0 16px' }}>
        {SECTOR_ROWS.map(s => (
          <div key={s.name} style={{ display: 'flex', padding: '7px 0', borderTop: `1px solid ${WF.rule2}`, fontSize: 13, gap: 10, alignItems: 'flex-start' }}>
            <span className="mono" style={{ width: 60, fontWeight: 600, color: s.dir > 0 ? WF.good : WF.bad, flexShrink: 0 }}>{s.ch}</span>
            <div style={{ flex: 1 }}>
              <span style={{ fontWeight: 600 }}>{s.name}</span>
              <span style={{ fontSize: 11, color: WF.ink3, marginLeft: 6 }}>{s.holds}</span>
              <div style={{ fontSize: 11, color: WF.ink3, marginTop: 2 }}>{s.note}</div>
            </div>
          </div>
        ))}
      </div>

      {/* POSITIONS */}
      <div style={{ padding: '16px 16px 6px', display: 'flex', alignItems: 'center', gap: 8 }}>
        <WFEyebrow>Positions · Δ since yesterday</WFEyebrow>
        <div style={{ flex: 1, height: 1, background: WF.rule2 }} />
      </div>
      <div style={{ padding: '0 16px' }}>
        {/* Mover */}
        <div style={{ padding: '12px 0', borderTop: `1px solid ${WF.ink}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <WFGrade grade="A" size="sm" delta={-1} />
            <span className="mono" style={{ fontSize: 14, fontWeight: 700, flex: 1 }}>NVDA</span>
            <span className="mono" style={{ fontSize: 10, color: WF.accent, fontWeight: 700 }}>8.2% of book</span>
          </div>
          <div style={{ fontSize: 12, color: WF.ink2, marginTop: 6, lineHeight: 1.45 }}>
            EU antitrust probe widened. News sentiment 71 → 58. Grade AA → A. Composite −5.
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
            <button style={{ padding: '6px 10px', border: `1px solid ${WF.ink}`, fontSize: 11, fontWeight: 600, fontFamily: WF.mono }}>Open NVDA →</button>
            <button style={{ padding: '6px 10px', border: `1px solid ${WF.rule}`, fontSize: 11, fontFamily: WF.mono }}>3 articles</button>
          </div>
        </div>
        {/* TLT slight improvement */}
        <div style={{ padding: '10px 0', borderTop: `1px solid ${WF.rule2}`, display: 'flex', alignItems: 'center', gap: 10 }}>
          <WFGrade grade="AA" size="sm" delta={+1} />
          <span className="mono" style={{ fontSize: 13, fontWeight: 700, flex: 1 }}>TLT</span>
          <span style={{ fontSize: 12, color: WF.ink2 }}>Score +1 · yield drifted down</span>
        </div>
        {/* Quiet block */}
        <div style={{ padding: '10px 0', borderTop: `1px solid ${WF.rule2}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 12, color: WF.ink3 }}>5 positions unchanged</span>
            <span className="mono" style={{ fontSize: 11, color: WF.ink3 }}>expand ▾</span>
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
            {['AAPL', 'MSFT', 'XOM', 'JPM', 'VOO'].map(t => (
              <div key={t} style={{ padding: '3px 8px', border: `1px solid ${WF.rule}`, fontFamily: WF.mono, fontSize: 11 }}>{t}</div>
            ))}
          </div>
        </div>
      </div>
      <div style={{ height: 8 }} />
      <WFTabBar active="digest" />
    </WFScreen>
  );
}

// ════════════════════════════════════════════════════════════════
//   D2 · Stacked cards — each section is a tight bordered card
//   Same sequence: macro card → sector card → position cards
// ════════════════════════════════════════════════════════════════
function DigestD2() {
  return (
    <WFScreen bg={WF.paper2}>
      <div style={{ padding: '10px 14px 8px', borderBottom: `1px solid ${WF.rule}`, background: WF.paper, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <WFEyebrow>May 6 · 7:02 AM</WFEyebrow>
          <div style={{ fontSize: 16, fontWeight: 600, marginTop: 2 }}>Morning Briefing</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <WFGrade grade="AA" size="sm" delta={0} />
          <div className="mono" style={{ fontSize: 11, color: WF.ink3 }}>81 ▼ 1</div>
        </div>
      </div>

      <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {/* MACRO CARD */}
        <div style={{ background: WF.paper, border: `1px solid ${WF.rule}`, padding: '12px 14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
            <WFEyebrow>Macro</WFEyebrow>
            <span className="mono" style={{ fontSize: 9, color: WF.ink4, background: WF.paper2, padding: '2px 6px', border: `1px solid ${WF.rule2}` }}>NO CHANGE</span>
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.55, color: WF.ink2 }}>
            Futures <span className="mono">+0.18%</span>. 10Y <span className="mono">4.31%</span> (−4bp). Crude <span className="mono">+1.8%</span> OPEC+. <b>Watch: CPI 08:30, Fed mins 14:00 ET.</b>
          </div>
        </div>

        {/* SECTOR CARD */}
        <div style={{ background: WF.paper, border: `1px solid ${WF.rule}`, padding: '12px 14px' }}>
          <WFEyebrow style={{ marginBottom: 8 }}>Sectors · your exposure</WFEyebrow>
          {SECTOR_ROWS.map((s, i) => (
            <div key={s.name} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '7px 0', borderTop: i === 0 ? `1px solid ${WF.rule}` : `1px solid ${WF.rule2}` }}>
              <span className="mono" style={{ fontSize: 12, fontWeight: 700, color: s.dir > 0 ? WF.good : WF.bad, width: 52, flexShrink: 0 }}>{s.ch}</span>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{s.name}</span>
                <span className="mono" style={{ fontSize: 10, color: WF.ink4, marginLeft: 6 }}>{s.holds}</span>
                <div style={{ fontSize: 11, color: WF.ink3, marginTop: 1 }}>{s.note}</div>
              </div>
            </div>
          ))}
        </div>

        {/* POSITION DIFF CARDS */}
        <WFEyebrow style={{ padding: '4px 2px 0' }}>Positions · overnight changes</WFEyebrow>

        {/* NVDA — high impact */}
        <div style={{ background: WF.paper, border: `1.5px solid ${WF.ink}`, padding: '12px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <WFGrade grade="A" size="sm" delta={-1} />
            <span className="mono" style={{ fontSize: 15, fontWeight: 700, flex: 1 }}>NVDA</span>
            <span className="mono" style={{ fontSize: 10, color: WF.accent, fontWeight: 700, border: `1px solid ${WF.accent}`, padding: '2px 5px' }}>8.2% BOOK</span>
          </div>
          <div style={{ display: 'flex', gap: 12, fontSize: 12 }}>
            <div style={{ flex: 1, color: WF.ink2, lineHeight: 1.45 }}>EU probe widened to GPU contracts. News sentiment 71 → 58. Grade AA → A.</div>
            <div style={{ width: 1, background: WF.rule2 }} />
            <div style={{ textAlign: 'center', flexShrink: 0 }}>
              <div className="mono" style={{ fontSize: 18, fontWeight: 700, color: WF.bad }}>−5</div>
              <div className="mono" style={{ fontSize: 9, color: WF.ink3 }}>SCORE</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
            <button style={{ flex: 1, padding: '7px 0', border: `1px solid ${WF.ink}`, fontSize: 11, fontWeight: 600 }}>Open NVDA →</button>
            <button style={{ flex: 1, padding: '7px 0', border: `1px solid ${WF.rule}`, fontSize: 11 }}>3 articles</button>
          </div>
        </div>

        {/* TLT — minor improvement */}
        <div style={{ background: WF.paper, border: `1px solid ${WF.rule}`, padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <WFGrade grade="AA" size="sm" delta={+1} />
          <span className="mono" style={{ fontSize: 13, fontWeight: 700, flex: 1 }}>TLT</span>
          <div style={{ textAlign: 'right' }}>
            <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: WF.good }}>+1</div>
            <div className="mono" style={{ fontSize: 9, color: WF.ink3 }}>SCORE</div>
          </div>
        </div>

        {/* Quiet collapsed */}
        <div style={{ background: WF.paper, border: `1px dashed ${WF.rule}`, padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ flex: 1, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {['AAPL', 'MSFT', 'XOM', 'JPM', 'VOO'].map(t => (
              <span key={t} className="mono" style={{ fontSize: 11, color: WF.ink3 }}>{t}</span>
            ))}
          </div>
          <span className="mono" style={{ fontSize: 11, color: WF.ink3 }}>all quiet ▾</span>
        </div>
      </div>

      <WFTabBar active="digest" />
    </WFScreen>
  );
}

// ════════════════════════════════════════════════════════════════
//   D3 · Tight ledger — dense single-column, ruled like a report
//   Macro and sector as brief labeled rows; positions as a ledger
// ════════════════════════════════════════════════════════════════
function DigestD3() {
  return (
    <WFScreen>
      {/* MASTHEAD */}
      <div style={{ padding: '10px 16px 8px', borderBottom: `2px solid ${WF.ink}` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
          <div>
            <div className="mono" style={{ fontSize: 10, color: WF.ink3, letterSpacing: 1 }}>CLAVIX DAILY · MAY 6 2026 · 7:02 AM ET</div>
            <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.5, marginTop: 2 }}>Morning Report</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <WFGrade grade="AA" size="md" delta={0} />
            <div className="mono" style={{ fontSize: 9, color: WF.ink3, marginTop: 3 }}>PORTFOLIO · 81/100</div>
          </div>
        </div>
      </div>

      {/* MACRO SECTION */}
      <div style={{ padding: '0 16px' }}>
        <div style={{ padding: '10px 0 4px', borderBottom: `1px solid ${WF.ink}` }}>
          <WFEyebrow>I. Macro</WFEyebrow>
        </div>
        <div style={{ fontSize: 13, lineHeight: 1.6, color: WF.ink2, padding: '8px 0', borderBottom: `1px solid ${WF.rule2}` }}>
          S&P futures <span className="mono">+0.18%</span>. 10Y yield <span className="mono">4.31%</span>, down 4bp overnight. Crude <span className="mono">+1.8%</span> on OPEC+ supply rollover. Dollar slipped. No macro shocks to report. <span className="mono" style={{ color: WF.ink }}>CPI 08:30 ET · Fed mins 14:00 ET</span> — the two risk events for your book today.
        </div>
      </div>

      {/* SECTOR SECTION */}
      <div style={{ padding: '0 16px' }}>
        <div style={{ padding: '10px 0 4px', borderBottom: `1px solid ${WF.ink}` }}>
          <WFEyebrow>II. Sector · your exposure</WFEyebrow>
        </div>
        {SECTOR_ROWS.map(s => (
          <div key={s.name} style={{ display: 'flex', padding: '7px 0', borderBottom: `1px solid ${WF.rule2}`, gap: 10, fontSize: 13 }}>
            <span className="mono" style={{ width: 52, fontWeight: 700, color: s.dir > 0 ? WF.good : WF.bad, flexShrink: 0 }}>{s.ch}</span>
            <span style={{ fontWeight: 600, width: 90, flexShrink: 0 }}>{s.name}</span>
            <span style={{ flex: 1, fontSize: 12, color: WF.ink3 }}>{s.note}</span>
          </div>
        ))}
      </div>

      {/* POSITIONS SECTION */}
      <div style={{ padding: '0 16px' }}>
        <div style={{ padding: '10px 0 4px', borderBottom: `1px solid ${WF.ink}` }}>
          <WFEyebrow>III. Positions · overnight delta</WFEyebrow>
        </div>

        {/* Header row */}
        <div className="mono" style={{ display: 'flex', padding: '5px 0', borderBottom: `1px solid ${WF.rule2}`, fontSize: 9, color: WF.ink3, letterSpacing: 0.5 }}>
          <span style={{ flex: 1 }}>TICKER / SUMMARY</span>
          <span style={{ width: 38, textAlign: 'right' }}>GRADE</span>
          <span style={{ width: 38, textAlign: 'right' }}>Δ</span>
        </div>

        {/* NVDA */}
        <div style={{ padding: '10px 0', borderBottom: `1px solid ${WF.rule}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', gap: 6, alignItems: 'baseline' }}>
                <span className="mono" style={{ fontSize: 14, fontWeight: 700 }}>NVDA</span>
                <span className="mono" style={{ fontSize: 10, color: WF.accent, fontWeight: 700 }}>8.2% of book</span>
              </div>
              <div style={{ fontSize: 12, color: WF.ink2, marginTop: 3, lineHeight: 1.4 }}>EU probe widened · news sentiment 71 → 58 · grade AA → A</div>
              <button style={{ marginTop: 5, fontSize: 11, color: WF.ink, fontFamily: WF.mono, borderBottom: `1px solid ${WF.rule}` }}>3 articles ›</button>
            </div>
            <WFGrade grade="A" size="xs" delta={-1} />
            <span className="mono" style={{ width: 38, textAlign: 'right', fontSize: 13, fontWeight: 700, color: WF.bad }}>−5</span>
          </div>
        </div>

        {/* TLT */}
        <div style={{ padding: '8px 0', borderBottom: `1px solid ${WF.rule2}`, display: 'flex', alignItems: 'center' }}>
          <div style={{ flex: 1 }}>
            <span className="mono" style={{ fontSize: 13, fontWeight: 700 }}>TLT</span>
            <span style={{ fontSize: 12, color: WF.ink3, marginLeft: 8 }}>Yield drifted down · score uptick</span>
          </div>
          <WFGrade grade="AA" size="xs" delta={+1} />
          <span className="mono" style={{ width: 38, textAlign: 'right', fontSize: 13, fontWeight: 700, color: WF.good }}>+1</span>
        </div>

        {/* Quiet */}
        {['AAPL', 'MSFT', 'XOM', 'JPM', 'VOO'].map(t => (
          <div key={t} style={{ padding: '6px 0', borderBottom: `1px solid ${WF.rule2}`, display: 'flex', alignItems: 'center' }}>
            <span className="mono" style={{ flex: 1, fontSize: 13, color: WF.ink3 }}>{t}</span>
            <span className="mono" style={{ fontSize: 11, color: WF.ink3 }}>no change</span>
            <span className="mono" style={{ width: 38, textAlign: 'right', fontSize: 12, color: WF.ink4 }}>—</span>
          </div>
        ))}
      </div>

      <div style={{ height: 10 }} />
      <WFTabBar active="digest" />
    </WFScreen>
  );
}

Object.assign(window, { DigestA, DigestB, DigestC, DigestD1, DigestD2, DigestD3 });
