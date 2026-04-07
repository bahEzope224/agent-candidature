import { useState, useEffect, useRef } from 'react';
import { API } from '../api';
import { useToast } from '../hooks/useToast';
import { Toasts } from '../components/Toasts';


const ADMIN_EMAIL = 'contact@ibrahima-bah.com';

const getAdminToken = () => sessionStorage.getItem('jat_admin');
const setAdminToken = t => sessionStorage.setItem('jat_admin', t);
const clearAdminToken = () => sessionStorage.removeItem('jat_admin');

async function adminApi(path, opts = {}) {
  const tok = getAdminToken();
  const hdrs = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  if (tok) hdrs['Authorization'] = `Bearer ${tok}`;
  const r = await fetch(API + path, { ...opts, headers: hdrs });
  if (r.status === 401) { clearAdminToken(); window.location.reload(); return null; }
  return r;
}

function QuotaBar({ used, limit, color }) {
  const pct = Math.min(100, (used / limit) * 100);
  const col = pct >= 100 ? 'var(--danger)' : pct >= 70 ? 'var(--warn)' : color || 'var(--mint)';
  return (
    <div className="quota-bar">
      <div className="quota-track">
        <div className="quota-fill" style={{ width: `${pct}%`, background: col }}></div>
      </div>
      <span style={{ fontSize: 10, fontFamily: 'DM Mono,monospace', color: 'var(--text-dim)' }}>{used}/{limit}</span>
    </div>
  );
}

/* ── AUTH WRAPPER — same split layout as main AuthPage ── */
function AdminAuthLayout({ children }) {
  return (
    <div className="auth-wrap">
      <div className="auth-left">
        <div className="auth-brand">Job<span>Agent</span></div>
        <div>
          <div className="auth-tagline">Panel<br /><span>Admin</span>istrateur</div>
          <div className="auth-desc" style={{ marginTop: 10 }}>
            Gestion des utilisateurs, quotas et statistiques d'usage.
          </div>
        </div>
        <div className="auth-features">
          {['Statistiques en temps réel', 'Gestion Premium / Freemium', 'Blocage & suppression', 'Reset des quotas'].map(f => (
            <div className="auth-feature" key={f}><div className="auth-dot"></div>{f}</div>
          ))}
        </div>
      </div>
      <div className="auth-right">
        <div className="auth-box">
          {children}
        </div>
      </div>
    </div>
  );
}

/* ── SETUP: création du compte admin ── */
function SetupBanner({ toast, onDone, onBack }) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  const create = async () => {
    setErr('');
    if (!password || password.length < 8) { setErr('Mot de passe trop court (min. 8 caractères)'); return; }
    if (password !== confirm) { setErr('Les mots de passe ne correspondent pas'); return; }
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: ADMIN_EMAIL, full_name: 'Admin', password }),
      });
      const d = await r.json();
      if (!r.ok) { setErr(d.detail || 'Erreur lors de la création'); setLoading(false); return; }
      toast.ok('Compte admin créé ✓ — vous pouvez maintenant vous connecter');
      onDone();
    } catch {
      setErr('Serveur inaccessible');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AdminAuthLayout>
      <div className="auth-title">⚙ Initialisation</div>
      <div className="auth-sub">Création du compte administrateur · usage unique</div>
      {err && <div className="auth-err">⚠ {err}</div>}
      <div className="form-grp">
        <label className="form-lbl">Email admin (verrouillé)</label>
        <input className="form-inp" value={ADMIN_EMAIL} readOnly disabled style={{ opacity: 0.6, cursor: 'not-allowed' }} />
      </div>
      <div className="form-grp">
        <label className="form-lbl">Mot de passe</label>
        <input
          className="form-inp"
          type="password"
          placeholder="Min. 8 caractères"
          value={password}
          onChange={e => setPassword(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && create()}
        />
        <div className="pw-hint">Min. 8 caractères</div>
      </div>
      <div className="form-grp">
        <label className="form-lbl">Confirmer</label>
        <input
          className="form-inp"
          type="password"
          placeholder="Répéter le mot de passe"
          value={confirm}
          onChange={e => setConfirm(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && create()}
        />
      </div>
      <button className="btn-submit" onClick={create} disabled={loading}>
        {loading && <span className="spinner"></span>}
        {loading ? 'Création...' : '➕ Créer le compte admin'}
      </button>
      <div className="auth-toggle">
        <a onClick={onBack}>◀ Revenir à la connexion</a>
      </div>
    </AdminAuthLayout>
  );
}

/* ── LOGIN ── */
function LoginPage({ onLogin, onSetup }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setErr(''); setLoading(true);
    try {
      const r = await fetch(`${API}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const d = await r.json();
      if (!r.ok) { setErr(d.detail || 'Erreur'); return; }
      setAdminToken(d.access_token);

      const ra = await fetch(`${API}/api/admin/stats`, {
        headers: { 'Authorization': `Bearer ${d.access_token}` }
      });
      if (ra.status === 403) { clearAdminToken(); setErr('Accès refusé — compte non autorisé'); return; }
      onLogin();
    } catch {
      setErr('Serveur inaccessible');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AdminAuthLayout>
      <div className="auth-title">🔐 Connexion Admin</div>
      <div className="auth-sub">Accès réservé aux administrateurs JobAgent</div>
      {err && <div className="auth-err">⚠ {err}</div>}
      <div className="form-grp">
        <label className="form-lbl">Email admin</label>
        <input className="form-inp" type="email" value={email} onChange={e => setEmail(e.target.value)} onKeyDown={e => e.key === 'Enter' && submit()} placeholder="contact@ibrahima-bah.com" />
      </div>
      <div className="form-grp">
        <label className="form-lbl">Mot de passe</label>
        <input className="form-inp" type="password" value={password} onChange={e => setPassword(e.target.value)} onKeyDown={e => e.key === 'Enter' && submit()} placeholder="••••••••" />
      </div>
      <button className="btn-submit" onClick={submit} disabled={loading}>
        {loading && <span className="spinner"></span>}
        {loading ? 'Connexion...' : 'Se connecter'}
      </button>
      <div className="auth-toggle">
        Première connexion ? <a onClick={onSetup}>Créer le compte admin</a>
      </div>
    </AdminAuthLayout>
  );
}

/* ── LOGS TERMINAL ─────────────────────────────────────────── */
function LogsTerminal({ toast }) {
  const [logs, setLogs] = useState(null);
  const [filter, setFilter] = useState('ALL');
  const [expanded, setExpanded] = useState(null);
  const bottomRef = useRef(null);

  const loadLogs = () =>
    adminApi('/api/admin/logs?limit=200').then(r => r?.json()).then(d => d && setLogs(d));

  const purgeLogs = async () => {
    if (!confirm('Supprimer tous les logs de plus de 30 jours ?')) return;
    const r = await adminApi('/api/admin/logs/purge', { method: 'DELETE' });
    if (r?.ok) { toast.ok('Logs anciens purgés'); loadLogs(); }
    else toast.err('Erreur lors de la purge');
  };

  useEffect(() => {
    loadLogs();
    const t = setInterval(loadLogs, 15000);
    return () => clearInterval(t);
  }, []);

  const LEVELS = ['ALL', 'FATAL', 'WARNING', 'INFO'];
  const LEVEL_COLOR = { FATAL: '#e05c5c', WARNING: '#e0a050', INFO: '#5ca8e0', DEFAULT: '#aaa' };
  const LEVEL_ICON = { FATAL: '🔴', WARNING: '🟡', INFO: '🔵' };

  const filtered = (logs || []).filter(l => filter === 'ALL' || l.level === filter);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
        <div style={{ display: 'flex', gap: 6 }}>
          {LEVELS.map(lv => (
            <button
              key={lv}
              onClick={() => setFilter(lv)}
              style={{
                padding: '4px 12px', borderRadius: 20, fontSize: 11, fontWeight: 600, border: 'none', cursor: 'pointer',
                background: filter === lv ? (LEVEL_COLOR[lv] || 'var(--mint)') : 'var(--surface)',
                color: filter === lv ? '#fff' : 'var(--text-dim)',
                transition: 'all 0.15s',
              }}
            >{lv}</button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-sm btn-sec" onClick={loadLogs}>↻ Actualiser</button>
          <button className="btn btn-sm btn-danger" onClick={purgeLogs}>🗑 Purger (+30j)</button>
        </div>
      </div>

      <div style={{
        background: '#0d1117', borderRadius: 12, padding: '14px 18px',
        fontFamily: 'DM Mono, monospace', fontSize: 11.5, lineHeight: 1.7,
        maxHeight: 520, overflowY: 'auto', border: '1px solid rgba(255,255,255,0.06)',
      }}>
        {logs === null ? (
          <div style={{ color: '#555', textAlign: 'center', padding: '40px 0' }}>Chargement des logs...</div>
        ) : filtered.length === 0 ? (
          <div style={{ color: '#555', textAlign: 'center', padding: '40px 0' }}>Aucun log{filter !== 'ALL' ? ` de niveau ${filter}` : ''} pour le moment.</div>
        ) : (
          filtered.map((log, i) => {
            const col = LEVEL_COLOR[log.level] || LEVEL_COLOR.DEFAULT;
            const ico = LEVEL_ICON[log.level] || '⚪';
            const isOpen = expanded === i;
            const date = new Date(log.created_at).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
            return (
              <div key={log.id || i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', padding: '6px 0' }}>
                <div
                  onClick={() => setExpanded(isOpen ? null : i)}
                  style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer', userSelect: 'none' }}
                >
                  <span style={{ color: '#555', whiteSpace: 'nowrap', fontSize: 10 }}>{date}</span>
                  <span style={{ color: col, fontWeight: 700, whiteSpace: 'nowrap' }}>{ico} {log.level}</span>
                  <span style={{ color: '#8b949e', whiteSpace: 'nowrap' }}>[{log.action}]</span>
                  <span style={{ color: '#cdd9e5', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: isOpen ? 'pre-wrap' : 'nowrap' }}>
                    {log.details?.email || log.details?.error || log.details?.url || '-'}
                  </span>
                  <span style={{ color: '#555', fontSize: 10 }}>{isOpen ? '▲' : '▼'}</span>
                </div>
                {isOpen && (
                  <pre style={{
                    margin: '6px 0 6px 26px', padding: '10px 14px', background: 'rgba(255,255,255,0.04)',
                    borderRadius: 8, color: '#adbac7', fontSize: 11, whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                    maxHeight: 240, overflowY: 'auto',
                  }}>{JSON.stringify(log.details, null, 2)}</pre>
                )}
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 8 }}>
        {filtered.length} log(s) • Rafraîchissement automatique toutes les 15s
      </div>
    </div>
  );
}

/* ── MINI SPARKLINE ─────────────────────────────────────────── */
function Sparkline({ data, color, height = 60, label }) {
  if (!data || data.length === 0) return null;
  const W = 400, H = height;
  const max = Math.max(...data.map(d => d.count), 1);
  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1)) * W;
    const y = H - (d.count / max) * H;
    return `${x},${y}`;
  }).join(' ');
  const areaPath = `M0,${H} L${data.map((d, i) => {
    const x = (i / (data.length - 1)) * W;
    const y = H - (d.count / max) * H;
    return `${x},${y}`;
  }).join(' L')} L${W},${H} Z`;

  return (
    <div>
      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 6, fontWeight: 600 }}>{label}</div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height, display: 'block' }} preserveAspectRatio="none">
        <path d={areaPath} fill={color} opacity="0.12" />
        <polyline points={pts} fill="none" stroke={color} strokeWidth="2" />
        {data.map((d, i) => d.count > 0 && (
          <circle key={i} cx={(i / (data.length - 1)) * W} cy={H - (d.count / max) * H} r="3" fill={color} />
        ))}
      </svg>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: 'var(--text-dim)', fontFamily: 'DM Mono,monospace', marginTop: 4 }}>
        <span>{data[0]?.date}</span>
        <span>{data[data.length - 1]?.date}</span>
      </div>
    </div>
  );
}

/* ── DONUT CHART ─────────────────────────────────────────────── */
function DonutChart({ segments }) {
  const total = segments.reduce((s, seg) => s + seg.value, 0);
  if (total === 0) return <div style={{ textAlign: 'center', color: 'var(--text-dim)', padding: 20 }}>Pas de données</div>;
  let cumulAngle = -90;
  const R = 70, cx = 90, cy = 90;

  const describeArc = (startAngle, angle) => {
    const sa = (startAngle * Math.PI) / 180, ea = ((startAngle + angle) * Math.PI) / 180;
    const x1 = cx + R * Math.cos(sa), y1 = cy + R * Math.sin(sa);
    const x2 = cx + R * Math.cos(ea), y2 = cy + R * Math.sin(ea);
    const large = angle > 180 ? 1 : 0;
    return `M ${cx} ${cy} L ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2} Z`;
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
      <svg viewBox="0 0 180 180" style={{ width: 180, flexShrink: 0 }}>
        {segments.map((seg, i) => {
          if (seg.value === 0) return null;
          const angle = (seg.value / total) * 360;
          const path = describeArc(cumulAngle, angle);
          cumulAngle += angle;
          return <path key={i} d={path} fill={seg.color} opacity={0.85} />;
        })}
        <circle cx={cx} cy={cy} r={42} fill="var(--surface)" />
        <text x={cx} y={cy - 6} textAnchor="middle" style={{ fontSize: 22, fontWeight: 700, fill: 'var(--text)', fontFamily: 'Syne,sans-serif' }}>{total}</text>
        <text x={cx} y={cy + 14} textAnchor="middle" style={{ fontSize: 9, fill: 'var(--text-dim)', fontFamily: 'DM Mono,monospace', textTransform: 'uppercase', letterSpacing: 0.5 }}>Total</text>
      </svg>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
        {segments.map((seg, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: seg.color, flexShrink: 0 }} />
            <div style={{ flex: 1, fontSize: 12, color: 'var(--text)' }}>{seg.label}</div>
            <div style={{ fontFamily: 'DM Mono,monospace', fontSize: 12, color: seg.color, fontWeight: 700 }}>{seg.value}</div>
            <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>{Math.round((seg.value / total) * 100)}%</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── CHARTS PANEL ─────────────────────────────────────────────── */
function StatsCharts({ stats }) {
  if (!stats) return <div className="loading"><span className="spinner"></span>Chargement...</div>;
  const a = stats.applications;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div className="card">
          <div className="card-hdr"><span className="card-ttl">👥 Inscriptions (30 jours)</span></div>
          <Sparkline data={stats.users.history_30d} color="#2db87a" height={70} label="Nouveaux utilisateurs / jour" />
        </div>
        <div className="card">
          <div className="card-hdr"><span className="card-ttl">📨 Candidatures (30 jours)</span></div>
          <Sparkline data={stats.applications.history_30d} color="#e0a050" height={70} label="Candidatures créées / jour" />
        </div>
      </div>
      <div className="card">
        <div className="card-hdr">
          <span className="card-ttl">📊 Funnel de conversion</span>
          <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>Taux entretien {a.conversion_rate}% · Taux signature {a.signing_rate}%</span>
        </div>
        <DonutChart segments={[
          { label: 'À postuler',  value: a.pending,    color: '#8b949e' },
          { label: 'Envoyées',    value: a.sent,       color: '#5ca8e0' },
          { label: 'Entretiens',  value: a.interviews, color: '#e0a050' },
          { label: '签署 Signés', value: a.signed,     color: '#2db87a' },
          { label: 'Refus',       value: a.refused,    color: '#e05c5c' },
        ]} />
      </div>
    </div>
  );
}

/* ── ADMIN PANEL (dashboard) ── */
function Panel({ toast }) {
  const [activeTab, setActiveTab] = useState('users');
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState(null);
  const [search, setSearch] = useState('');
  const [busy, setBusy] = useState({});

  const loadStats = () => adminApi('/api/admin/stats').then(r => r?.json()).then(d => d && setStats(d));
  const loadUsers = () => adminApi('/api/admin/users').then(r => r?.json()).then(d => d && setUsers(d));

  useEffect(() => {
    loadStats();
    loadUsers();
  }, []);

  const action = async (userId, endpoint, method, msg) => {
    setBusy(p => ({ ...p, [userId + endpoint]: true }));
    try {
      const r = await adminApi(`/api/admin/users/${userId}/${endpoint}`, { method });
      const d = await r.json();
      if (!r.ok) { toast.err(d.detail || 'Erreur'); return; }
      toast.ok(d.message || msg);
      loadUsers();
      loadStats();
    } catch {
      toast.err('Erreur réseau');
    } finally {
      setBusy(p => ({ ...p, [userId + endpoint]: false }));
    }
  };

  const deleteUser = async (userId, email) => {
    if (!confirm(`Supprimer définitivement ${email} et toutes ses données ?`)) return;
    setBusy(p => ({ ...p, [userId + 'del']: true }));
    try {
      const r = await adminApi(`/api/admin/users/${userId}`, { method: 'DELETE' });
      const d = await r.json();
      toast.ok(d.message || 'Compte supprimé');
      loadUsers();
      loadStats();
    } catch {
      toast.err('Erreur');
    } finally {
      setBusy(p => ({ ...p, [userId + 'del']: false }));
    }
  };

  const filtered = users?.filter(u =>
    u.email.toLowerCase().includes(search.toLowerCase()) ||
    u.full_name.toLowerCase().includes(search.toLowerCase())
  ) || [];

  return (
    <div>
      {/* Admin topbar */}
      <div style={{
        background: 'var(--text)', padding: '13px 20px', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between'
      }}>
        <div className="topbar-brand" style={{ color: 'var(--bg)' }}>Job<span>Agent</span></div>
        <span className="badge b-warn" style={{ fontSize: 9, letterSpacing: '0.5px' }}>⚙ ADMIN</span>
        <button
          onClick={() => { clearAdminToken(); window.location.reload(); }}
          className="btn btn-ghost"
          style={{ color: 'rgba(255,255,255,0.4)', borderColor: 'rgba(255,255,255,0.1)', fontSize: 11 }}
        >↩ Déconnexion</button>
      </div>

      <div className="main" style={{ maxWidth: 1100, margin: '0 auto' }}>
        <div className="page-header">
          <div className="page-title">Panel Administrateur</div>
          <div className="page-sub">Gestion des utilisateurs et statistiques d'usage · JobAgent Bêta</div>
        </div>

        {/* KPI CARDS */}
        {!stats ? (
          <div className="loading"><span className="spinner"></span>Chargement...</div>
        ) : (
          <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10, marginBottom: 20 }}>
            {[
              { c: 'c-mint',  lbl: 'Utilisateurs',   val: stats.users.total,            sub: `+${stats.users.new_this_week} cette semaine` },
              { c: 'c-warn',  lbl: 'Premium',         val: stats.users.premium,          sub: `${stats.users.freemium} freemium` },
              { c: 'c-cream', lbl: 'Candidatures',    val: stats.applications.total,     sub: `${stats.applications.sent} envoyées` },
              { c: 'c-mint',  lbl: 'Entretiens',      val: stats.applications.interviews,sub: `Taux ${stats.applications.conversion_rate}%` },
              { c: 'c-mint',  lbl: '✅ Signés',        val: stats.applications.signed,    sub: `${stats.applications.signing_rate}% taux` },
              { c: 'c-danger',lbl: '❌ Refus',          val: stats.applications.refused,   sub: '' },
            ].map(s => (
              <div className={`stat-card ${s.c}`} key={s.lbl}>
                <div className="stat-lbl">{s.lbl}</div>
                <div className="stat-val">{s.val}</div>
                {s.sub && <div className="stat-sub">{s.sub}</div>}
              </div>
            ))}
          </div>
        )}

        {/* TABS */}
        <div style={{ display: 'flex', gap: 4, margin: '4px 0 14px', borderBottom: '1px solid var(--border)' }}>
          {[
            { id: 'users', label: '👥 Utilisateurs' },
            { id: 'charts', label: '📊 Graphiques' },
            { id: 'logs', label: '🖥️ Logs & Erreurs' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '8px 18px', background: 'none', border: 'none',
                borderBottom: activeTab === tab.id ? '2px solid var(--mint)' : '2px solid transparent',
                color: activeTab === tab.id ? 'var(--mint)' : 'var(--text-dim)',
                fontWeight: activeTab === tab.id ? 700 : 400, cursor: 'pointer', fontSize: 13, transition: 'all 0.15s',
              }}
            >{tab.label}</button>
          ))}
        </div>

        {/* USERS TABLE */}
        {activeTab === 'users' && (
        <div className="card">
          <div className="card-hdr">
            <span className="card-ttl">👥 Utilisateurs ({users?.length || 0})</span>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <input className="form-inp" style={{ width: 200, padding: '7px 11px', fontSize: 12 }} placeholder="🔍 Rechercher..." value={search} onChange={e => setSearch(e.target.value)} />
              <button className="btn btn-sec btn-sm" onClick={() => { loadUsers(); loadStats(); }}>↻ Actualiser</button>
            </div>
          </div>
          {!users ? (
            <div className="loading"><span className="spinner"></span>Chargement...</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    {['Utilisateur', 'Plan', 'Statut', 'Candidatures', 'Scraping/j', 'Scoring/j', 'Inscription', 'Actions'].map(h => (
                      <th key={h} style={{
                        padding: '9px 14px', textAlign: 'left', fontSize: '9.5px',
                        fontFamily: 'DM Mono, monospace', textTransform: 'uppercase',
                        letterSpacing: '0.7px', color: 'var(--text-dim)',
                        borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap'
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(u => (
                    <tr key={u.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '12px 14px', fontSize: '12.5px' }}>
                        <div style={{ fontWeight: 500, fontSize: 13 }}>{u.full_name}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'DM Mono,monospace' }}>{u.email}</div>
                      </td>
                      <td style={{ padding: '12px 14px' }}>
                        {u.is_premium
                          ? <span className="badge b-mint">⭐ Premium</span>
                          : <span className="badge b-dim">Freemium</span>}
                      </td>
                      <td style={{ padding: '12px 14px' }}>
                        {u.is_active
                          ? <span className="badge b-mint">● Actif</span>
                          : <span className="badge b-danger">● Bloqué</span>}
                      </td>
                      <td style={{ padding: '12px 14px' }}>
                        <QuotaBar used={u.applications_this_month} limit={u.is_premium ? 999 : 5} />
                        <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 2 }}>{u.applications_count} total</div>
                      </td>
                      <td style={{ padding: '12px 14px' }}><QuotaBar used={u.scrapings_today} limit={u.is_premium ? 999 : 2} /></td>
                      <td style={{ padding: '12px 14px' }}><QuotaBar used={u.scoring_today} limit={u.is_premium ? 999 : 10} /></td>
                      <td style={{ padding: '12px 14px', fontSize: 11, color: 'var(--text-dim)', fontFamily: 'DM Mono,monospace' }}>
                        {new Date(u.created_at).toLocaleDateString('fr-FR')}
                      </td>
                      <td style={{ padding: '12px 14px' }}>
                        <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                          <button
                            className={`btn btn-sm ${u.is_premium ? 'btn-sec' : 'btn-mint'}`}
                            onClick={() => action(u.id, 'toggle-premium', 'PATCH', u.is_premium ? 'Passé en freemium' : 'Passé en premium ⭐')}
                            disabled={busy[u.id + 'toggle-premium']}
                          >
                            {u.is_premium ? '↓ Free' : '⭐ Prem'}
                          </button>
                          <button
                            className={`btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-sec'}`}
                            onClick={() => action(u.id, 'toggle-active', 'PATCH', u.is_active ? 'Compte bloqué' : 'Compte activé')}
                            disabled={busy[u.id + 'toggle-active']}
                          >
                            {u.is_active ? '🔒' : '✓'}
                          </button>
                          <button
                            className="btn btn-sm btn-sec"
                            onClick={() => action(u.id, 'reset-quotas', 'PATCH', 'Quotas réinitialisés')}
                            disabled={busy[u.id + 'reset-quotas']}
                            title="Réinitialiser les quotas"
                          >↻</button>
                          <button
                            className="btn btn-sm btn-danger"
                            onClick={() => deleteUser(u.id, u.email)}
                            disabled={busy[u.id + 'del']}
                            title="Supprimer le compte"
                          >🗑</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        )}

        {/* CHARTS TAB */}
        {activeTab === 'charts' && (
          <StatsCharts stats={stats} />
        )}

        {/* LOGS TERMINAL */}
        {activeTab === 'logs' && (
          <div className="card">
            <div className="card-hdr">
              <span className="card-ttl">🖥️ Terminal d'Activité & Erreurs</span>
              <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>Rafraîchissement auto • Purge auto des logs +30j</span>
            </div>
            <LogsTerminal toast={toast} />
          </div>
        )}

      </div>
    </div>
  );
}

/* ── EXPORT ── */
export function AdminPanel() {
  const [logged, setLogged] = useState(!!getAdminToken());
  const [showSetup, setShowSetup] = useState(false);
  const toast = useToast();

  useEffect(() => {
    document.title = "Admin — JobAgent";
  }, []);

  return (
    <>
      {!logged ? (
        !showSetup ? (
          <LoginPage onLogin={() => setLogged(true)} onSetup={() => setShowSetup(true)} />
        ) : (
          <SetupBanner toast={toast} onDone={() => setShowSetup(false)} onBack={() => setShowSetup(false)} />
        )
      ) : (
        <Panel toast={toast} />
      )}
      <Toasts items={toast.items} />
    </>
  );
}
