import { useState, useEffect } from 'react';
import { api as baseApi, API } from '../api';
import { useToast } from '../hooks/useToast';

const ADMIN_EMAIL = 'contact@ibrahima-bah.com';

const getTitle = () => { document.title = "Admin — JobAgent"; };
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

function SetupBanner({ toast, onDone }) {
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
    <div className="setup-banner">
      <div className="setup-title">⚙ Initialisation du compte administrateur</div>
      <div className="setup-sub">Ce formulaire est à usage unique. Il disparaît dès que le compte est créé.</div>
      {err && <div className="auth-err" style={{ marginBottom: 12 }}>⚠ {err}</div>}
      <div className="setup-grid">
        <div className="setup-field">
          <span className="setup-label">Email admin (fixe)</span>
          <input className="setup-input readonly" value={ADMIN_EMAIL} readOnly disabled />
        </div>
        <div className="setup-field">
          <span className="setup-label">Mot de passe</span>
          <input
            className="setup-input"
            type="password"
            placeholder="Min. 8 caractères"
            value={password}
            onChange={e => setPassword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && create()}
          />
        </div>
        <div className="setup-field">
          <span className="setup-label">Confirmer le mot de passe</span>
          <input
            className="setup-input"
            type="password"
            placeholder="Répéter le mot de passe"
            value={confirm}
            onChange={e => setConfirm(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && create()}
          />
        </div>
      </div>
      <div className="setup-footer">
        <button className="btn-create" onClick={create} disabled={loading}>
          {loading ? <><span className="spinner"></span> Création...</> : '➕ Créer le compte admin'}
        </button>
        <span className="setup-note">L'email est verrouillé sur {ADMIN_EMAIL}</span>
      </div>
    </div>
  );
}

function LoginPage({ onLogin }) {
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
    <div className="auth-wrap">
      <div className="auth-box">
        <div className="auth-title">🔐 Admin</div>
        <div className="auth-sub">Accès réservé aux administrateurs JobAgent</div>
        {err && <div className="auth-err">⚠ {err}</div>}
        <div className="form-grp"><label className="form-lbl">Email admin</label><input className="form-inp" type="email" value={email} onChange={e => setEmail(e.target.value)} onKeyDown={e => e.key === 'Enter' && submit()} placeholder="contact@ibrahima-bah.com" /></div>
        <div className="form-grp"><label className="form-lbl">Mot de passe</label><input className="form-inp" type="password" value={password} onChange={e => setPassword(e.target.value)} onKeyDown={e => e.key === 'Enter' && submit()} placeholder="••••••••" /></div>
        <button className="btn-submit" onClick={submit} disabled={loading}>
          {loading ? <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}><span className="spinner"></span>Connexion...</span> : 'Se connecter'}
        </button>
      </div>
    </div>
  );
}

function Panel({ toast }) {
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
    // eslint-disable-next-line no-restricted-globals
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
      <div className="topbar">
        <div className="brand">Job<span>Agent</span></div>
        <span className="admin-badge">⚙ ADMIN</span>
        <button className="logout-btn" onClick={() => { clearAdminToken(); window.location.reload(); }}>↩ Déconnexion</button>
      </div>

      <div className="main">
        <div className="page-title">Panel Administrateur</div>
        <div className="page-sub">Gestion des utilisateurs et statistiques d'usage · JobAgent Bêta</div>

        {!stats ? (
          <div className="loading"><span className="spinner spinner-dark"></span>Chargement...</div>
        ) : (
          <div className="stats-grid">
            {[
              { c: 'c-mint', lbl: 'Utilisateurs', val: stats.users.total, sub: `${stats.users.new_this_week} cette semaine` },
              { c: 'c-warn', lbl: 'Premium', val: stats.users.premium, sub: `${stats.users.freemium} freemium` },
              { c: 'c-cream', lbl: 'Candidatures', val: stats.applications.total, sub: `${stats.applications.sent} envoyées · ${stats.applications.interviews} entretiens` },
              { c: 'c-dim', lbl: 'Offres scrapées', val: stats.jobs.total, sub: `${stats.users.active} comptes actifs` },
            ].map(s => (
              <div className={`stat-card ${s.c}`} key={s.lbl}>
                <div className="stat-lbl">{s.lbl}</div>
                <div className="stat-val">{s.val}</div>
                <div className="stat-sub">{s.sub}</div>
              </div>
            ))}
          </div>
        )}

        <div className="table-card">
          <div className="table-hdr">
            <span className="table-ttl">👥 Utilisateurs ({users?.length || 0})</span>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <input className="search-inp" placeholder="🔍 Rechercher..." value={search} onChange={e => setSearch(e.target.value)} />
              <button className="btn btn-sec" onClick={() => { loadUsers(); loadStats(); }}>↻ Actualiser</button>
            </div>
          </div>
          {!users ? (
            <div className="loading"><span className="spinner spinner-dark"></span>Chargement...</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Utilisateur</th>
                    <th>Plan</th>
                    <th>Statut</th>
                    <th>Candidatures</th>
                    <th>Scraping/j</th>
                    <th>Scoring/j</th>
                    <th>Inscription</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(u => (
                    <tr key={u.id}>
                      <td>
                        <div style={{ fontWeight: 500, fontSize: 13 }}>{u.full_name}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'DM Mono,monospace' }}>{u.email}</div>
                      </td>
                      <td>
                        {u.is_premium
                          ? <span className="badge b-mint">⭐ Premium</span>
                          : <span className="badge b-dim">Freemium</span>}
                      </td>
                      <td>
                        {u.is_active
                          ? <span className="badge b-mint">● Actif</span>
                          : <span className="badge b-danger">● Bloqué</span>}
                      </td>
                      <td>
                        <QuotaBar used={u.applications_this_month} limit={u.is_premium ? 999 : 5} />
                        <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 2 }}>{u.applications_count} total</div>
                      </td>
                      <td><QuotaBar used={u.scrapings_today} limit={u.is_premium ? 999 : 2} /></td>
                      <td><QuotaBar used={u.scoring_today} limit={u.is_premium ? 999 : 10} /></td>
                      <td style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'DM Mono,monospace' }}>
                        {new Date(u.created_at).toLocaleDateString('fr-FR')}
                      </td>
                      <td>
                        <div className="actions">
                          <button
                            className={`btn ${u.is_premium ? 'btn-sec' : 'btn-mint'}`}
                            onClick={() => action(u.id, 'toggle-premium', 'PATCH', u.is_premium ? 'Passé en freemium' : 'Passé en premium ⭐')}
                            disabled={busy[u.id + 'toggle-premium']}
                          >
                            {u.is_premium ? '↓ Freemium' : '⭐ Premium'}
                          </button>
                          <button
                            className={`btn ${u.is_active ? 'btn-warn' : 'btn-sec'}`}
                            onClick={() => action(u.id, 'toggle-active', 'PATCH', u.is_active ? 'Compte bloqué' : 'Compte activé')}
                            disabled={busy[u.id + 'toggle-active']}
                          >
                            {u.is_active ? '🔒 Bloquer' : '✓ Activer'}
                          </button>
                          <button
                            className="btn btn-sec"
                            onClick={() => action(u.id, 'reset-quotas', 'PATCH', 'Quotas réinitialisés')}
                            disabled={busy[u.id + 'reset-quotas']}
                            title="Réinitialiser les quotas"
                          >↻</button>
                          <button
                            className="btn btn-danger"
                            onClick={() => deleteUser(u.id, u.email)}
                            disabled={busy[u.id + 'del']}
                            title="Supprimer le compte"
                          >🗑</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {filtered.length === 0 && (
                    <tr><td colSpan={8} style={{ textAlign: 'center', padding: 32, color: 'var(--text-dim)' }}>Aucun utilisateur trouvé</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function AdminPanel() {
  const [logged, setLogged] = useState(!!getAdminToken());
  const [showSetup, setShowSetup] = useState(false);
  const toast = useToast();

  useEffect(() => {
    getTitle();
  }, []);

  return (
    <>
      {!logged ? (
        <div>
          <LoginPage onLogin={() => setLogged(true)} />
          <div style={{ textAlign: 'center', marginTop: -20, paddingBottom: 30 }}>
            {!showSetup ? (
              <button
                onClick={() => setShowSetup(true)}
                style={{ background: 'none', border: 'none', fontSize: 11, color: 'var(--text-dim)', cursor: 'pointer', textDecoration: 'underline', fontFamily: 'DM Sans,sans-serif' }}
              >
                Première connexion ? Créer le compte admin
              </button>
            ) : (
              <div style={{ maxWidth: 600, margin: '0 auto', padding: '0 20px' }}>
                <SetupBanner toast={toast} onDone={() => setShowSetup(false)} />
              </div>
            )}
          </div>
        </div>
      ) : (
        <Panel toast={toast} />
      )}
    </>
  );
}
