export function ScoreBar({ s }) {
  if (!s) return <span style={{ color: 'var(--text-dim)', fontSize: 10.5 }}>—</span>;
  const col = s >= 80 ? 'var(--mint)' : s >= 60 ? 'var(--warn)' : 'var(--danger)';
  return (
    <div className="score-bar">
      <div className="score-track">
        <div className="score-fill" style={{ width: `${s}%`, background: col }}></div>
      </div>
      <span className="score-n">{s}</span>
    </div>
  );
}
