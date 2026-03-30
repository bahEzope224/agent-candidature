import { useState, useEffect } from 'react';
import { api } from '../api';
import { TagInput } from '../components/TagInput';

export function ProfilePage({ toast, user }) {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState('info');
  const [pw, setPw] = useState({ cur: '', nxt: '', cfm: '' });
  const [pwErr, setPwErr] = useState('');
  const [pwLoading, setPwLoading] = useState(false);
  
  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));
  
  useEffect(() => { 
    api('/api/profile/').then(r => r?.json()).then(d => { 
      if (d && !d.detail) setForm(d); 
    }); 
  }, []);
  
  const save = async () => { 
    setSaving(true); 
    try { 
      const r = await api('/api/profile/', { method: 'PATCH', body: JSON.stringify(form) }); 
      if (r.ok) { 
        toast.ok('Sauvegardé ✓'); 
      } else { 
        const d = await r.json(); 
        toast.err(d.detail || 'Erreur'); 
      } 
    } catch { 
      toast.err('Erreur réseau'); 
    } finally { 
      setSaving(false); 
    } 
  };
  
  const changePw = async () => { 
    setPwErr(''); 
    if (pw.nxt !== pw.cfm) { setPwErr('Mots de passe différents'); return; } 
    if (pw.nxt.length < 8) { setPwErr('Min. 8 caractères'); return; } 
    setPwLoading(true); 
    try { 
      const r = await api('/api/auth/change-password', { method: 'POST', body: JSON.stringify({ current_password: pw.cur, new_password: pw.nxt }) }); 
      const d = await r.json(); 
      if (r.ok) { 
        toast.ok('Modifié ✓'); 
        setPw({ cur: '', nxt: '', cfm: '' }); 
      } else {
        setPwErr(d.detail || 'Erreur'); 
      }
    } catch { 
      setPwErr('Erreur réseau'); 
    } finally { 
      setPwLoading(false); 
    } 
  };
  
  if (!form) return <div className="loading"><span className="spinner"></span>Chargement...</div>;
  
  const initials = ((form.first_name || '')[0] || '') + ((form.last_name || '')[0] || '');
  const TABS = [
    { k: 'info', ico: '👤', l: 'Infos' }, 
    { k: 'skills', ico: '⚡', l: 'Skills' }, 
    { k: 'search', ico: '🎯', l: 'Recherche' }, 
    { k: 'text', ico: '✍️', l: 'Textes' }, 
    { k: 'security', ico: '🔒', l: 'Sécurité' }
  ];

  const profileContent = (
    <div>
      {tab === 'info' && <div>
        <div className="fsec"><div className="fsec-ttl">👤 Identité</div>
          <div className="form-row">
            <div className="form-grp"><label className="form-lbl">Prénom</label><input className="form-inp" value={form.first_name || ''} onChange={e => set('first_name', e.target.value)} /></div>
            <div className="form-grp"><label className="form-lbl">Nom</label><input className="form-inp" value={form.last_name || ''} onChange={e => set('last_name', e.target.value)} /></div>
          </div>
          <div className="form-row">
            <div className="form-grp"><label className="form-lbl">Téléphone</label><input className="form-inp" value={form.phone || ''} onChange={e => set('phone', e.target.value)} placeholder="+33 6..." /></div>
            <div className="form-grp"><label className="form-lbl">Localisation</label><input className="form-inp" value={form.location || ''} onChange={e => set('location', e.target.value)} placeholder="Paris" /></div>
          </div>
          <div className="form-grp"><label className="form-lbl">LinkedIn</label><input className="form-inp" value={form.linkedin_url || ''} onChange={e => set('linkedin_url', e.target.value)} placeholder="linkedin.com/in/..." /></div>
          <div className="form-grp"><label className="form-lbl">GitHub / Portfolio</label><input className="form-inp" value={form.portfolio_url || ''} onChange={e => set('portfolio_url', e.target.value)} placeholder="github.com/..." /></div>
        </div>
        <div className="fsec"><div className="fsec-ttl">🎓 Formation</div>
          <div className="form-row">
            <div className="form-grp"><label className="form-lbl">Niveau</label><input className="form-inp" value={form.education_level || ''} onChange={e => set('education_level', e.target.value)} placeholder="Master Data Science" /></div>
            <div className="form-grp"><label className="form-lbl">École</label><input className="form-inp" value={form.school || ''} onChange={e => set('school', e.target.value)} placeholder="Paris-Saclay" /></div>
          </div>
          <div className="form-grp"><label className="form-lbl">Année diplôme</label><input className="form-inp" value={form.graduation_year || ''} onChange={e => set('graduation_year', e.target.value)} placeholder="2026" style={{ maxWidth: 110 }} /></div>
        </div>
      </div>}
      
      {tab === 'skills' && <div>
        <div className="fsec"><div className="fsec-ttl">⚡ Tech</div>
          <div className="form-grp"><label className="form-lbl">Compétences techniques</label><TagInput values={form.skills_technical || []} onChange={v => set('skills_technical', v)} placeholder="Python, SQL..." /></div>
          <div className="form-grp" style={{ marginTop: 11 }}><label className="form-lbl">Outils</label><TagInput values={form.tools || []} onChange={v => set('tools', v)} placeholder="Power BI, Tableau..." /></div>
        </div>
        <div className="fsec"><div className="fsec-ttl">🤝 Soft skills</div><TagInput values={form.skills_soft || []} onChange={v => set('skills_soft', v)} placeholder="Rigueur..." /></div>
        <div className="fsec"><div className="fsec-ttl">🌍 Langues</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>Format : "Français - Natif"</div>
          <TagInput values={form.languages?.map(l => typeof l === 'object' ? `${l.lang} - ${l.level}` : l) || []} onChange={v => set('languages', v.map(s => { const p = s.split(' - '); return { lang: p[0], level: p[1] || '' }; }))} placeholder="Français - Natif" />
        </div>
      </div>}
      
      {tab === 'search' && <div>
        <div className="fsec"><div className="fsec-ttl">🎯 Objectif</div>
          <div className="form-grp"><label className="form-lbl">Postes visés</label><TagInput values={form.target_roles || []} onChange={v => set('target_roles', v)} placeholder="Data Analyst..." /></div>
          <div className="form-grp" style={{ marginTop: 11 }}><label className="form-lbl">Localisations</label><TagInput values={form.target_locations || []} onChange={v => set('target_locations', v)} placeholder="Paris, Remote..." /></div>
          <div className="form-row" style={{ marginTop: 11 }}>
            <div className="form-grp"><label className="form-lbl">Contrat</label>
              <select className="form-inp" value={form.target_contract || 'stage'} onChange={e => set('target_contract', e.target.value)}>
                <option value="stage">Stage</option>
                <option value="alternance">Alternance</option>
                <option value="cdi">CDI</option>
                <option value="cdd">CDD</option>
              </select>
            </div>
            <div className="form-grp"><label className="form-lbl">Disponibilité</label><input className="form-inp" value={form.availability_date || ''} onChange={e => set('availability_date', e.target.value)} placeholder="Sept. 2025" /></div>
          </div>
        </div>
      </div>}
      
      {tab === 'text' && <div>
        <div style={{ padding: '9px 12px', background: 'var(--mint-light)', border: '1px solid var(--mint-mid)', borderRadius: 8, marginBottom: 16, fontSize: 12, color: 'var(--mint-dark)' }}>💡 Ces textes guident GPT pour personnaliser chaque candidature.</div>
        <div className="fsec"><div className="fsec-ttl">✍️ Présentation</div>
          <div className="form-grp"><label className="form-lbl">Pitch</label><textarea className="form-inp" value={form.pitch || ''} onChange={e => set('pitch', e.target.value)} placeholder="Étudiant en Master Data Science..." /></div>
          <div className="form-grp"><label className="form-lbl">Points forts</label><textarea className="form-inp" value={form.strengths || ''} onChange={e => set('strengths', e.target.value)} placeholder="Projet Kaggle Top 5%..." /></div>
          <div className="form-grp"><label className="form-lbl">Motivation</label><textarea className="form-inp" value={form.motivation || ''} onChange={e => set('motivation', e.target.value)} placeholder="Passionné par la data..." /></div>
        </div>
      </div>}
      
      {tab === 'security' && <div>
        <div className="fsec"><div className="fsec-ttl">🔒 Changer le mot de passe</div>
          {pwErr && <div className="auth-err" style={{ marginBottom: 11 }}>⚠ {pwErr}</div>}
          <div className="form-grp"><label className="form-lbl">Actuel</label><input className="form-inp" type="password" value={pw.cur} onChange={e => setPw(p => ({ ...p, cur: e.target.value }))} /></div>
          <div className="form-grp"><label className="form-lbl">Nouveau</label><input className="form-inp" type="password" value={pw.nxt} onChange={e => setPw(p => ({ ...p, nxt: e.target.value }))} /></div>
          <div className="form-grp"><label className="form-lbl">Confirmer</label><input className="form-inp" type="password" value={pw.cfm} onChange={e => setPw(p => ({ ...p, cfm: e.target.value }))} /></div>
          <button className="btn btn-primary" onClick={changePw} disabled={pwLoading}>{pwLoading ? <span className="spinner"></span> : '🔒'} Modifier</button>
        </div>
        <div className="fsec"><div className="fsec-ttl">ℹ️ Protections</div>
          {[['Chiffrement', 'bcrypt rounds=12'], ['Tokens', 'JWT 7j'], ['Sessions', 'sessionStorage — non partagé']].map(([k, v]) => (
            <div className="sec-info-row" key={k}><span className="sec-key">{k}</span><span className="sec-val">{v}</span></div>
          ))}
        </div>
      </div>}
    </div>
  );

  return (
    <div>
      <div className="topbar">
        <div className="topbar-brand">Profil</div>
        {tab !== 'security' && <button className="btn btn-mint btn-sm" onClick={save} disabled={saving}>{saving ? <span className="spinner"></span> : '💾'}</button>}
      </div>
      <div className="page-header">
        <div>
          <div className="page-title">Mon Profil</div>
          <div className="page-sub">Personnalise tes candidatures</div>
        </div>
        {tab !== 'security' && (
          <button className="btn btn-mint" onClick={save} disabled={saving}>
            {saving ? <span className="spinner"></span> : '💾'} Sauvegarder
          </button>
        )}
      </div>
      <div id="profile-mobile">
        <div className="card" style={{ padding: '18px 14px', textAlign: 'center', marginBottom: 12 }}>
          <div className="p-avatar">{initials.toUpperCase() || '?'}</div>
          <div className="p-name">{form.first_name} {form.last_name}</div>
          <div className="p-email">{user?.email}</div>
          <div className="p-stats">
            <div><div className="p-stat-v">{form.skills_technical?.length || 0}</div><div className="p-stat-l">Skills</div></div>
            <div><div className="p-stat-v">{form.target_roles?.length || 0}</div><div className="p-stat-l">Postes</div></div>
            <div><div className="p-stat-v">{form.languages?.length || 0}</div><div className="p-stat-l">Langues</div></div>
          </div>
        </div>
        <div className="p-tabs">
          {TABS.map(t => <button key={t.k} className={`p-tab ${tab === t.k ? 'on' : ''}`} onClick={() => setTab(t.k)}>{t.ico} {t.l}</button>)}
        </div>
        <div className="card" style={{ padding: '14px' }}>{profileContent}</div>
      </div>
      
      <div id="profile-desktop" style={{ display: 'none' }}>
        <div className="p-profile-desktop">
          <div>
            <div className="p-side-card">
              <div className="p-avatar">{initials.toUpperCase() || '?'}</div>
              <div className="p-name">{form.first_name} {form.last_name}</div>
              <div className="p-email">{user?.email}</div>
              <div className="p-stats">
                <div><div className="p-stat-v">{form.skills_technical?.length || 0}</div><div className="p-stat-l">Skills</div></div>
                <div><div className="p-stat-v">{form.target_roles?.length || 0}</div><div className="p-stat-l">Postes</div></div>
                <div><div className="p-stat-v">{form.languages?.length || 0}</div><div className="p-stat-l">Langues</div></div>
              </div>
            </div>
            <div className="p-nav-desktop">
              {TABS.map(t => <div key={t.k} className={`p-nav-item ${tab === t.k ? 'on' : ''}`} onClick={() => setTab(t.k)}><span>{t.ico}</span>{t.l}</div>)}
            </div>
          </div>
          <div className="card" style={{ height: 'fit-content' }}>
            <div style={{ padding: '18px' }}>{profileContent}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
