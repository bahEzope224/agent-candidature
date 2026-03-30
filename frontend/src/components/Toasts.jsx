export function Toasts({ items }) {
  return (
    <div className="toast-wrap">
      {items.map(t => (
        <div key={t.id} className={`toast ${t.type}`}>
          <span>{t.type === 'success' ? '✓' : t.type === 'error' ? '✕' : 'ℹ'}</span>{t.msg}
        </div>
      ))}
    </div>
  );
}
