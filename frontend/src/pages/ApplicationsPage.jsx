import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { SBadge } from '../components/SBadge';
import { KanbanBoard } from '../components/KanbanBoard';
import { SwipeMode } from '../components/SwipeMode';

const isMobile = () => window.innerWidth < 768;

export function ApplicationsPage({ toast }) {
  const [apps, setApps] = useState(null);
  const [filter, setFilter] = useState('all');
  const [sel, setSel] = useState(null);
  const [gen, setGen] = useState(false);
  const [mobile, setMobile] = useState(isMobile());
  const [view, setView] = useState(() => isMobile() ? 'swipe' : (localStorage.getItem('appView') || 'kanban'));
  const [swipeMode, setSwipeMode] = useState(() => isMobile());
  const navigate = useNavigate();

  // Écoute le redimensionnement
  useEffect(() => {
    const handler = () => {
      const m = isMobile();
      setMobile(m);
      if (!m) { setSwipeMode(false); setView(localStorage.getItem('appView') || 'kanban'); }
      else { setSwipeMode(true); }
    };
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  const load = () => api('/api/applications/').then(r => r?.json()).then(d => d && setApps(d));
  useEffect(() => { load(); }, []);

  const filtered = apps ? apps.filter(a => {
    if (filter === 'all') return true;
    if (filter === 'pending') return ['to_apply', 'follow_up_needed'].includes(a.status);
    if (filter === 'sent') return a.status === 'sent';
    if (filter === 'interview') return ['interview', 'interview_proposed'].includes(a.status);
    if (filter === 'followup') return ['follow_up_sent', 'follow_up_needed'].includes(a.status);
    if (filter === 'no_response') return a.status === 'no_response';
    return a.status === 'refused';
  }) : [];

  const loadDet = async id => { 
    const r = await api(`/api/applications/${id}`); 
    const d = await r.json(); 
    setSel(d); 
  };

  const confirmAction = async (id, action, msg, reload) => {
    try {
      await api(`/api/applications/${id}/${action}`, { method: 'PATCH' });
      toast.ok(msg);
      reload();
    } catch { 
      toast.err('Erreur'); 
    }
  };

  const updateStatus = async (id, status) => {
    try {
      await api(`/api/applications/${id}/status?status=${status}`, { method: 'PATCH' });
      load();
    } catch {
      toast.err('Erreur lors de la mise à jour');
    }
  };

  const genBatch = async () => { 
    setGen(true); 
    try { 
      const r = await api('/api/applications/generate-batch?limit=5', { method: 'POST' }); 
      const d = await r.json(); 
      toast.ok(`${d.generated} candidature(s)`); 
      load(); 
    } catch { 
      toast.err('Erreur'); 
    } finally { 
      setGen(false); 
    } 
  };

  const FILTERS = [
    { k: 'all', l: 'Toutes' }, 
    { k: 'pending', l: '📋 À candidater' }, 
    { k: 'sent', l: '📨 Envoyées' }, 
    { k: 'followup', l: '🔁 À relancer' }, 
    { k: 'no_response', l: '😶 Sans réponse' }, 
    { k: 'interview', l: '🎯 Entretiens' }, 
    { k: 'refused', l: '✕ Refus' }
  ];

  return (
    <div>
      <div className="topbar">
        <div className="topbar-brand">Candidatures</div>
        <button className="btn btn-mint btn-sm" onClick={genBatch} disabled={gen}>
          {gen ? <span className="spinner"></span> : '✨'}
        </button>
      </div>
      <div className="page-header">
        <div>
          <div className="page-title">Candidatures</div>
          <div className="page-sub">{apps ? `${apps.length} au total` : ''}</div>
        </div>
        <div className="hdr-actions">
          <button className="btn btn-sec btn-sm" onClick={() => api('/api/applications/check-followup-deadlines', { method: 'POST' }).then(() => { toast.info('Relances vérifiées'); load(); })}>
            🔁 Relances
          </button>
          <button className="btn btn-mint btn-sm" onClick={genBatch} disabled={gen}>
            {gen ? <span className="spinner"></span> : '✨'} Générer
          </button>
        </div>
      </div>
        <div className="filter-bar" style={{ justifyContent: 'space-between' , display:'none'}}>
          <div style={{ display: 'flex', gap: 6, overflowX: 'auto' }}>
            {FILTERS.map(f => (
              <button key={f.k} className={`fbtn ${filter === f.k ? 'on' : ''}`} onClick={() => setFilter(f.k)}>
                {f.l}
              </button>
            ))}
          </div>

          {!mobile ? (
            <div className="view-toggle" style={{ display: 'flex', background: 'var(--surface2)', padding: 2, borderRadius: 8 }}>
              <button className={`btn btn-sm ${view === 'list' ? 'btn-primary' : 'btn-ghost'}`} style={{ border: 'none' }} onClick={() => { setView('list'); localStorage.setItem('appView', 'list'); }}>☰</button>
              <button className={`btn btn-sm ${view === 'kanban' ? 'btn-primary' : 'btn-ghost'}`} style={{ border: 'none' }} onClick={() => { setView('kanban'); localStorage.setItem('appView', 'kanban'); }}>◈</button>
            </div>
          ) : (
            <button
              className="btn btn-sm btn-mint"
              style={{ border: 'none', fontSize: 13, fontWeight: 700, borderRadius: 8, padding: '6px 12px' }}
              onClick={() => setSwipeMode(true)}
            >🃏 Swipe</button>
          )}
        </div>

        {/* SWIPE MODE */}
        {swipeMode && apps && (
          <SwipeMode
            apps={apps}
            onStatusChange={updateStatus}
            onClose={() => {
              if (mobile) navigate('/dashboard');
              else setSwipeMode(false);
            }}
            showClose={!mobile}
          />
        )}

        {/* Kanban/List: Desktop only */}
        {!mobile && view === 'kanban' && apps && (
          <KanbanBoard apps={apps} onStatusChange={updateStatus} onDetails={loadDet} />
        )}

        {!mobile && view === 'list' && (
         <div className="card">
           {!apps ? (
             <div className="loading"><span className="spinner"></span>Chargement...</div>
           ) : filtered.length === 0 ? (
             <div className="empty"><div className="empty-ico">📭</div><div>Aucune candidature</div></div>
           ) : filtered.map(a => (
             <div className="list-item" key={a.id}>
               <div className="list-item-row" onClick={() => loadDet(a.id)} style={{ cursor: 'pointer' }}>
                 <div className="list-item-title">{a.offer}</div>
                 <SBadge s={a.status} />
               </div>
               {/* Rest of list item content */}
               <div className="list-item-meta">
                 <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>{a.company}</span>
                 {a.confidence && (
                   <span style={{ fontFamily: 'DM Mono,monospace', fontSize: 10.5, color: a.confidence >= 0.85 ? 'var(--mint-dark)' : 'var(--warn)' }}>
                     {Math.round(a.confidence * 100)}%
                   </span>
                 )}
                 <span style={{ fontFamily: 'DM Mono,monospace', fontSize: 10, color: 'var(--text-dim)' }}>{new Date(a.created_at).toLocaleDateString('fr-FR')}</span>
               </div>
               <div style={{ display: 'flex', gap: 5, marginTop: 5, flexWrap: 'wrap' }}>
                 {a.status === 'to_apply' && <>
                   <button className="btn btn-mint btn-sm" onClick={() => confirmAction(a.id, 'confirm-sent', 'Envoyé ✓', load)}>✅ Envoyé</button>
                   <button className="btn btn-ghost btn-sm" onClick={() => loadDet(a.id)}>📄 Voir mail</button>
                 </>}
                 {a.status === 'follow_up_needed' && <>
                   <button className="btn btn-sec btn-sm" onClick={() => confirmAction(a.id, 'confirm-followup-sent', 'Relance confirmée ✓', load)}>🔁 J'ai relancé</button>
                   <button className="btn btn-ghost btn-sm" onClick={() => loadDet(a.id)}>📄 Voir relance</button>
                 </>}
                 {['sent', 'follow_up_sent', 'follow_up_needed', 'no_response'].includes(a.status) && <>
                   <button className="btn btn-mint btn-sm" onClick={() => confirmAction(a.id, 'confirm-interview', '🎯 Entretien enregistré !', load)}>🎯 Entretien</button>
                   <button className="btn btn-sm" style={{ background: 'var(--danger-light)', color: 'var(--danger)', border: '1px solid rgba(192,57,43,0.2)' }} onClick={() => confirmAction(a.id, 'confirm-refused', 'Refus enregistré', load)}>✕ Refus</button>
                 </>}
               </div>
             </div>
           ))}
         </div>
       )}
      
      {sel && (
        <div className="modal-ov" onClick={() => setSel(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-handle"></div>
            <div className="modal-ttl">{sel.offer}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 11 }}>{sel.company}</div>
            
            <div style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'DM Mono,monospace', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 4 }}>Sujet</div>
            <div style={{ fontSize: 12.5, padding: '8px 11px', background: 'var(--bg)', borderRadius: 7, border: '1px solid var(--border-strong)', marginBottom: 11 }}>{sel.email_subject}</div>
            
            <div style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'DM Mono,monospace', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 4 }}>Email</div>
            <div className="email-pre">{sel.email_body}</div>
            
            <div style={{ display: 'flex', gap: 6, marginTop: 9, flexWrap: 'wrap', alignItems: 'center' }}>
              <SBadge s={sel.status} />
              {sel.status === 'to_apply' && (
                <span className="badge b-dim" style={{ fontSize: 11, padding: '3px 8px' }}>En attente de validation</span>
              )}
              {sel.confidence && <span className="badge b-dim">Confiance : {Math.round(sel.confidence * 100)}%</span>}
            </div>

            <div style={{ display: 'flex', gap: 6, marginTop: 11, flexWrap: 'wrap' }}>
              {sel.status === 'to_apply' && <button className="btn btn-mint btn-sm" onClick={async () => { await api(`/api/applications/${sel.id}/confirm-sent`, { method: 'PATCH' }); toast.ok('Marqué comme envoyé ✓'); setSel(null); load(); }}>✅ J'ai postulé</button>}
              {sel.status === 'follow_up_needed' && <button className="btn btn-sec btn-sm" onClick={async () => { await api(`/api/applications/${sel.id}/confirm-followup-sent`, { method: 'PATCH' }); toast.ok('Relance confirmée ✓'); setSel(null); load(); }}>🔁 J'ai relancé</button>}
              {['sent', 'follow_up_sent', 'follow_up_needed'].includes(sel.status) && <button className="btn btn-mint btn-sm" onClick={async () => { await api(`/api/applications/${sel.id}/confirm-interview`, { method: 'PATCH' }); toast.ok('Entretien enregistré 🎯'); setSel(null); load(); }}>🎯 Entretien obtenu</button>}
              {['sent', 'follow_up_sent', 'no_response'].includes(sel.status) && <button className="btn btn-sm" style={{ background: 'var(--danger-light)', color: 'var(--danger)', border: '1px solid rgba(192,57,43,0.2)' }} onClick={async () => { await api(`/api/applications/${sel.id}/confirm-refused`, { method: 'PATCH' }); toast.info('Refus enregistré'); setSel(null); load(); }}>✕ Refus</button>}
            </div>

            {sel.cover_letter && (
              <div style={{ marginTop: 14 }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'DM Mono,monospace', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 4 }}>Lettre de motivation</div>
                <div className="email-pre">{sel.cover_letter}</div>
                <button className="btn btn-ghost btn-sm" style={{ marginTop: 6 }} onClick={() => { navigator.clipboard.writeText(sel.cover_letter); toast.ok('Lettre copiée !'); }}>📋 Copier la lettre</button>
              </div>
            )}
            
            {sel.email_body && (
              <div style={{ marginTop: 10, display: 'flex', gap: 6 }}>
                <button className="btn btn-ghost btn-sm" onClick={() => { navigator.clipboard.writeText(sel.email_subject + '\n\n' + sel.email_body); toast.ok('Mail copié !'); }}>📋 Copier le mail</button>
                {sel.offer_url && <a href={sel.offer_url} target="_blank" rel="noreferrer" className="btn btn-mint btn-sm">🔗 Voir & candidater</a>}
              </div>
            )}
            
            {sel.followup_email_body && (
              <div style={{ marginTop: 14 }}>
                <div style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'DM Mono,monospace', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 4 }}>Mail de relance — à copier-coller</div>
                <div className="email-pre">{sel.followup_email_body}</div>
                <button className="btn btn-ghost btn-sm" style={{ marginTop: 6 }} onClick={() => { navigator.clipboard.writeText(sel.followup_email_body); toast.ok('Relance copiée !'); }}>📋 Copier la relance</button>
              </div>
            )}
            
            <div className="modal-foot">
              <button className="btn btn-ghost" onClick={() => setSel(null)}>Fermer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
