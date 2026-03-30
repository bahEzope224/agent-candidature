import { useState } from 'react';
import { API, setToken, setUser } from '../api';

export function AuthPage({ onLogin }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ email: '', password: '', full_name: '' });
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);
  
  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));
  
  const submit = async () => {
    setErr('');
    if (!form.email || !form.password) { setErr('Champs requis'); return; }
    if (mode === 'register' && !form.full_name) { setErr('Nom requis'); return; }
    setLoading(true);
    
    try {
      const body = mode === 'login' ? { email: form.email, password: form.password } : { email: form.email, password: form.password, full_name: form.full_name };
      const r = await fetch(`${API}/api/auth/${mode === 'login' ? 'login' : 'register'}`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify(body) 
      });
      const d = await r.json();
      if (!r.ok) { setErr(d.detail || 'Erreur'); return; }
      
      const user = { id: d.user_id, email: d.email, full_name: d.full_name };
      setToken(d.access_token); 
      setUser(user); 
      onLogin(user);
    } catch { 
      setErr('Serveur inaccessible'); 
    } finally { 
      setLoading(false); 
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-left">
        <div className="auth-brand">Job<span>Agent</span></div>
        <div>
          <div className="auth-tagline">Ton agent IA<br />pour décrocher<br />ton <span>job</span></div>
          <div className="auth-desc" style={{ marginTop: 10 }}>Scraping, scoring, candidatures et relances auto.</div>
        </div>
        <div className="auth-features">
          {['Scraping WTTJ + Indeed', 'Scoring GPT-4o-mini', 'Candidatures auto', 'Relances J+7'].map(f => (
            <div className="auth-feature" key={f}><div className="auth-dot"></div>{f}</div>
          ))}
        </div>
      </div>
      <div className="auth-right">
        <div className="auth-box">
          <div className="auth-title">{mode === 'login' ? 'Connexion' : 'Créer un compte'}</div>
          <div className="auth-sub">{mode === 'login' ? 'Accède à ton dashboard' : 'Configure ton agent'}</div>
          {err && <div className="auth-err">⚠ {err}</div>}
          {mode === 'register' && (
            <div className="form-grp">
              <label className="form-lbl">Prénom & Nom</label>
              <input className="form-inp" placeholder="Prenom Nom" value={form.full_name} onChange={e => set('full_name', e.target.value)} onKeyDown={e => e.key === 'Enter' && submit()} />
            </div>
          )}
          <div className="form-grp">
            <label className="form-lbl">Email</label>
            <input className="form-inp" type="email" placeholder="ton@email.com" value={form.email} onChange={e => set('email', e.target.value)} onKeyDown={e => e.key === 'Enter' && submit()} />
          </div>
          <div className="form-grp">
            <label className="form-lbl">Mot de passe</label>
            <input className="form-inp" type="password" placeholder={mode === 'register' ? 'Min. 8 cars, 1 maj, 1 chiffre' : '••••••••'} value={form.password} onChange={e => set('password', e.target.value)} onKeyDown={e => e.key === 'Enter' && submit()} />
            {mode === 'register' && <div className="pw-hint">Min. 8 caractères · 1 majuscule · 1 chiffre</div>}
          </div>
          <button className="btn-submit" onClick={submit} disabled={loading}>
            {loading && <span className="spinner"></span>}
            {loading ? '...' : (mode === 'login' ? 'Se connecter' : 'Créer mon compte')}
          </button>
          <div className="auth-toggle">
            {mode === 'login' ? (
              <>Pas de compte ? <a onClick={() => { setMode('register'); setErr(''); }}>Créer</a></>
            ) : (
              <>Déjà inscrit ? <a onClick={() => { setMode('login'); setErr(''); }}>Se connecter</a></>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
