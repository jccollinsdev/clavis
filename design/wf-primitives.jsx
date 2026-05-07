// wf-primitives.jsx — shared wireframe building blocks for Clavix mocks.
// Clean fintech wireframe vibe: sharp boxes, mono+sans pair, B&W with a
// single accent for "interactive" / "user data" emphasis.

const WF = {
  ink: '#111418',
  ink2: '#3a3f46',
  ink3: '#6b7280',
  ink4: '#9aa1ab',
  rule: '#d9dce1',
  rule2: '#e8eaee',
  paper: '#ffffff',
  paper2: '#f5f6f7',
  // Single accent — used sparingly to mark "personalised" / hot data
  accent: '#c2410c', // burnt orange, not too saturated
  accentSoft: '#fdebd9',
  good: '#1f6f43',
  goodSoft: '#e3f1e9',
  warn: '#a35a00',
  warnSoft: '#faecd6',
  bad: '#9a1d1d',
  badSoft: '#f4dada',
  sans: 'ui-sans-serif, -apple-system, "SF Pro Text", "Inter", system-ui, sans-serif',
  mono: 'ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace',
};

// Inject base reset for everything inside a wireframe screen.
if (typeof document !== 'undefined' && !document.getElementById('wf-styles')) {
  const s = document.createElement('style');
  s.id = 'wf-styles';
  s.textContent = `
    .wf, .wf * { box-sizing: border-box; }
    .wf { font-family: ${WF.sans}; color: ${WF.ink}; background: ${WF.paper}; -webkit-font-smoothing: antialiased; }
    .wf .mono { font-family: ${WF.mono}; font-feature-settings: "tnum"; }
    .wf hr { border: 0; border-top: 1px solid ${WF.rule}; margin: 0; }
    .wf button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; }
  `;
  document.head.appendChild(s);
}

// ───────────────────────── Screen shell ─────────────────────────
// Wraps screen content. Children fill the iPhone viewport (390x844).
// Includes status-bar spacer (47px) and bottom safe-area (34px) by default.
function WFScreen({ children, statusBar = true, homeIndicator = true, scroll = true, bg = WF.paper, style = {} }) {
  return (
    <div
      className="wf"
      style={{
        width: '100%', height: '100%', background: bg,
        display: 'flex', flexDirection: 'column',
        overflow: scroll ? 'hidden' : 'visible',
        ...style,
      }}
    >
      {statusBar && <WFStatusBar />}
      <div style={{ flex: 1, overflow: scroll ? 'auto' : 'visible', position: 'relative' }}>
        {children}
      </div>
      {homeIndicator && (
        <div style={{ height: 34, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <div style={{ width: 134, height: 5, borderRadius: 3, background: WF.ink }} />
        </div>
      )}
    </div>
  );
}

// Stripped-down monochrome status bar (no liquid glass).
function WFStatusBar({ time = '7:02' }) {
  return (
    <div style={{
      height: 47, display: 'flex', alignItems: 'flex-end',
      justifyContent: 'space-between', padding: '0 22px 10px',
      flexShrink: 0,
    }}>
      <span style={{ fontFamily: WF.sans, fontWeight: 600, fontSize: 15 }}>{time}</span>
      <span className="mono" style={{ fontSize: 11, color: WF.ink2, letterSpacing: 0.4 }}>•••  ◐  ▮▮▮</span>
    </div>
  );
}

// ───────────────────────── App-level chrome ─────────────────────
function WFAppBar({ title, leading, trailing, subtitle, sticky = true }) {
  return (
    <div style={{
      position: sticky ? 'sticky' : 'static', top: 0, zIndex: 5,
      background: WF.paper, borderBottom: `1px solid ${WF.rule}`,
      padding: '8px 16px 12px', display: 'flex', alignItems: 'center', gap: 8,
    }}>
      <div style={{ width: 28, display: 'flex', justifyContent: 'flex-start' }}>{leading}</div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
        <span style={{ fontWeight: 600, fontSize: 15, letterSpacing: -0.1 }}>{title}</span>
        {subtitle && <span className="mono" style={{ fontSize: 10, color: WF.ink3 }}>{subtitle}</span>}
      </div>
      <div style={{ width: 28, display: 'flex', justifyContent: 'flex-end' }}>{trailing}</div>
    </div>
  );
}

function WFTabBar({ active = 'digest' }) {
  const tabs = [
    { id: 'digest', label: 'Today', glyph: '◧' },
    { id: 'portfolio', label: 'Holdings', glyph: '▤' },
    { id: 'search', label: 'Search', glyph: '◯' },
    { id: 'alerts', label: 'Alerts', glyph: '◔' },
    { id: 'settings', label: 'Settings', glyph: '⊜' },
  ];
  return (
    <div style={{
      borderTop: `1px solid ${WF.rule}`, background: WF.paper,
      display: 'flex', padding: '8px 4px 4px', flexShrink: 0,
    }}>
      {tabs.map(t => (
        <div key={t.id} style={{
          flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
          color: t.id === active ? WF.ink : WF.ink4,
        }}>
          <span style={{ fontSize: 18, lineHeight: 1 }}>{t.glyph}</span>
          <span style={{ fontSize: 10, fontWeight: t.id === active ? 600 : 400 }}>{t.label}</span>
        </div>
      ))}
    </div>
  );
}

// ───────────────────────── Type / utility ───────────────────────
function WFEyebrow({ children, style }) {
  return (
    <div className="mono" style={{
      fontSize: 10, letterSpacing: 0.8, textTransform: 'uppercase',
      color: WF.ink3, ...style,
    }}>{children}</div>
  );
}
function WFRule({ style }) { return <div style={{ height: 1, background: WF.rule, ...style }} />; }
function WFDashed({ style }) {
  return <div style={{ height: 1, backgroundImage: `linear-gradient(to right, ${WF.rule} 50%, transparent 0)`, backgroundSize: '6px 1px', backgroundRepeat: 'repeat-x', ...style }} />;
}

// ───────────────────────── Grade pill ───────────────────────────
// Bond-rating-style grade. Style is intentionally flat / monochrome so the
// vibe stays "rating agency" rather than "trading hype".
function WFGrade({ grade = 'AA', size = 'md', delta }) {
  const sizes = {
    xs: { w: 28, h: 18, fs: 10, p: 0 },
    sm: { w: 36, h: 22, fs: 11, p: 0 },
    md: { w: 48, h: 28, fs: 14, p: 0 },
    lg: { w: 78, h: 50, fs: 24, p: 0 },
    hero: { w: 130, h: 96, fs: 48, p: 0 },
  };
  const s = sizes[size] || sizes.md;
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <div style={{
        width: s.w, height: s.h,
        border: `1.5px solid ${WF.ink}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: WF.mono, fontWeight: 700, fontSize: s.fs, letterSpacing: 0.5,
        background: WF.paper, color: WF.ink,
      }}>{grade}</div>
      {delta !== undefined && delta !== null && (
        <span className="mono" style={{ fontSize: s.fs * 0.55, color: delta === 0 ? WF.ink3 : (delta > 0 ? WF.good : WF.bad), fontWeight: 600 }}>
          {delta === 0 ? '—' : (delta > 0 ? '▲' : '▼')} {delta !== 0 ? Math.abs(delta) : ''}
        </span>
      )}
    </div>
  );
}

// ───────────────────────── Score bar (0-100) ────────────────────
function WFScoreBar({ score = 70, label, sub, height = 6 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {(label || sub) && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          {label && <span style={{ fontSize: 12, color: WF.ink2 }}>{label}</span>}
          {sub && <span className="mono" style={{ fontSize: 11, color: WF.ink }}>{sub}</span>}
        </div>
      )}
      <div style={{ position: 'relative', height, background: WF.rule2, borderRadius: 0 }}>
        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${score}%`, background: WF.ink }} />
        {[20, 40, 60, 80].map(t => (
          <div key={t} style={{ position: 'absolute', left: `${t}%`, top: -1, bottom: -1, width: 1, background: WF.paper }} />
        ))}
      </div>
    </div>
  );
}

// Vertical bar variant for the 5-dimension row.
function WFDimensionBar({ name, score, abbrev }) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <div style={{ height: 56, width: 18, background: WF.rule2, position: 'relative' }}>
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: `${score}%`, background: WF.ink }} />
      </div>
      <span className="mono" style={{ fontSize: 11, fontWeight: 600 }}>{score}</span>
      <span style={{ fontSize: 9, color: WF.ink3, textAlign: 'center', lineHeight: 1.15 }}>{abbrev || name}</span>
    </div>
  );
}

// ───────────────────────── Sparkline ────────────────────────────
function WFSparkline({ data, width = 80, height = 24, stroke = WF.ink, fill }) {
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      {fill && <polyline points={`0,${height} ${pts} ${width},${height}`} fill={fill} stroke="none" />}
      <polyline points={pts} fill="none" stroke={stroke} strokeWidth="1.25" />
    </svg>
  );
}

// ───────────────────────── Annotation (margin note) ─────────────
// Used liberally per the user's request. Sits OUTSIDE the iPhone frame
// usually, but can also be rendered inside as a callout.
function WFNote({ children, side = 'right', label }) {
  return (
    <div style={{
      fontFamily: WF.mono, fontSize: 11, lineHeight: 1.4,
      color: WF.ink2, background: '#fffbe8',
      border: `1px solid #e8d97a`, padding: '8px 10px',
      maxWidth: 220, position: 'relative',
    }}>
      {label && (
        <div className="mono" style={{
          fontSize: 9, letterSpacing: 0.8, textTransform: 'uppercase',
          color: WF.warn, fontWeight: 700, marginBottom: 3,
        }}>{label}</div>
      )}
      {children}
    </div>
  );
}

// Inline callout / hint inside a screen (different visual register from
// WFNote — the dotted-arrow design-doc kind).
function WFCallout({ children, kind = 'info' }) {
  const kinds = {
    info: { bg: '#f3f4f6', border: WF.rule, ic: 'i' },
    warn: { bg: WF.warnSoft, border: '#e6c98a', ic: '!' },
    pro: { bg: WF.accentSoft, border: '#e8b890', ic: '★' },
  };
  const k = kinds[kind] || kinds.info;
  return (
    <div style={{
      display: 'flex', gap: 8, padding: '8px 10px',
      background: k.bg, border: `1px dashed ${k.border}`,
      fontSize: 12, color: WF.ink2, lineHeight: 1.35,
    }}>
      <span className="mono" style={{ fontWeight: 700 }}>{k.ic}</span>
      <span>{children}</span>
    </div>
  );
}

// ───────────────────────── Img placeholder / chart frame ────────
function WFBox({ height = 80, label, style }) {
  return (
    <div style={{
      height, border: `1px dashed ${WF.rule}`, background: WF.paper2,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: WF.mono, fontSize: 10, color: WF.ink3, letterSpacing: 0.4,
      ...style,
    }}>{label}</div>
  );
}

// Strip diagonal pattern for "limited data" / placeholder.
function WFHashFill({ height = 80, label, style }) {
  return (
    <div style={{
      height,
      backgroundImage: `repeating-linear-gradient(135deg, ${WF.rule2} 0 6px, transparent 6px 12px)`,
      border: `1px solid ${WF.rule}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: WF.mono, fontSize: 10, color: WF.ink3, letterSpacing: 0.4,
      ...style,
    }}>{label}</div>
  );
}

// ───────────────────────── Locked / Pro badge ───────────────────
function WFProBadge({ size = 10 }) {
  return (
    <span className="mono" style={{
      display: 'inline-flex', alignItems: 'center', gap: 3,
      fontSize: size, fontWeight: 700, letterSpacing: 0.6,
      color: WF.accent, border: `1px solid ${WF.accent}`,
      padding: '1px 5px', textTransform: 'uppercase',
    }}>★ Pro</span>
  );
}

function WFLockedRow({ children }) {
  return (
    <div style={{
      padding: '10px 12px',
      background: 'repeating-linear-gradient(135deg, #fafafa 0 8px, #f3f4f6 8px 16px)',
      border: `1px solid ${WF.rule}`,
      display: 'flex', alignItems: 'center', gap: 10,
      color: WF.ink3, fontSize: 13,
    }}>
      <span className="mono" style={{ fontWeight: 700 }}>⌧</span>
      <span style={{ flex: 1 }}>{children}</span>
      <WFProBadge />
    </div>
  );
}

// ───────────────────────── Section header inside a screen ────────
function WFSectionHeader({ eyebrow, title, action }) {
  return (
    <div style={{
      padding: '20px 16px 8px', display: 'flex',
      flexDirection: 'column', gap: 2,
    }}>
      {eyebrow && <WFEyebrow>{eyebrow}</WFEyebrow>}
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
        <span style={{ fontWeight: 600, fontSize: 17 }}>{title}</span>
        {action && <span className="mono" style={{ fontSize: 11, color: WF.ink2 }}>{action}</span>}
      </div>
    </div>
  );
}

// Export everything to window so other Babel scripts can use it.
Object.assign(window, {
  WF, WFScreen, WFStatusBar, WFAppBar, WFTabBar,
  WFEyebrow, WFRule, WFDashed, WFGrade, WFScoreBar, WFDimensionBar,
  WFSparkline, WFNote, WFCallout, WFBox, WFHashFill, WFProBadge,
  WFLockedRow, WFSectionHeader,
});
