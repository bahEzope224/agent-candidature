import { useState, useEffect } from 'react';
import { api } from '../api';
import { ScoreBar } from '../components/ScoreBar';

export function OffersPage({ toast }) {
  const [jobs, setJobs] = useState(null);
  const [filter, setFilter] = useState('all');
  const [scoring, setScoring] = useState(false);
  const [gf, setGf] = useState({});
  const [df, setDf] = useState({});

  const load = () => api('/api/jobs/').then(r => r?.json()).then(d => d && setJobs(d));
  useEffect(() => { load(); }, []);

  const filtered = jobs ? jobs.filter(j => filter === 'all' ? true : j.status === filter) : [];

  const scoreAll = async () => {
    setScoring(true);
    try { 
      const r = await api('/api/jobs/score-all', { method: 'POST' }); 
      const d = await r.json(); 
      toast.ok(`${d.scored} offres scorées`); 
      load(); 
    } catch { 
      toast.err('Erreur'); 
    } finally { 
      setScoring(false); 
    }
  };

  const gen = async id => {
    setGf(p => ({ ...p, [id]: true }));
    try { 
      await api(`/api/applications/generate/${id}`, { method: 'POST' }); 
      toast.ok('Candidature générée !'); 
    } catch { 
      toast.err('Erreur'); 
    } finally { 
      setGf(p => ({ ...p, [id]: false })); 
    }
  };

  const delOffer = async id => {
    setDf(p => ({ ...p, [id]: true }));
    try {
      await api(`/api/jobs/${id}`, { method: 'DELETE' });
      toast.ok('Offre supprimée');
      load();
    } catch { 
      toast.err('Erreur lors de la suppression'); 
    } finally { 
      setDf(p => ({ ...p, [id]: false })); 
    }
  };

  const delAll = async () => {
    // eslint-disable-next-line no-restricted-globals
    if (!confirm(`Supprimer toutes les offres ${filter !== 'all' ? `(${filter})` : ''} ?`)) return;
    try {
      const url = filter !== 'all' ? `/api/jobs/?status=${filter}` : '/api/jobs/';
      await api(url, { method: 'DELETE' });
      toast.ok('Offres supprimées');
      load();
    } catch { 
      toast.err('Erreur'); 
    }
  };

  const FILTERS = [
    { k: 'all', l: 'Toutes' }, 
    { k: 'to_review', l: '🔍 À analyser' }, 
    { k: 'shortlisted', l: '⭐ Shortlistées' }, 
    { k: 'ignored', l: '✕ Ignorées' }
  ];

  return (
    <div>
      <div className="topbar">
        <div className="topbar-brand">Offres</div>
        <button className="btn btn-sec btn-sm" onClick={scoreAll} disabled={scoring}>
          {scoring ? <span className="spinner"></span> : '⚡'}
        </button>
      </div>
      <div className="page-header">
        <div>
          <div className="page-title">Offres d'emploi</div>
          <div className="page-sub">{jobs ? `${jobs.length} en base` : ''}</div>
        </div>
        <div className="hdr-actions">
          <button className="btn btn-sec btn-sm" onClick={scoreAll} disabled={scoring}>
            {scoring ? <span className="spinner"></span> : '⚡'} Matcher
          </button>
          <button className="btn btn-mint btn-sm" onClick={async () => {
            toast.info('🔍 Recherche en cours... (30-60 sec)');
            const r = await api('/api/jobs/scrape', { method: 'POST' });
            if (!r || !r.ok) { toast.err('Erreur de recherche'); return; }
            let attempts = 0;
            const poll = setInterval(async () => {
              attempts++;
              const rj = await api('/api/jobs/');
              const jobsData = await rj.json();
              if (jobsData && jobsData.length > 0) { 
                clearInterval(poll); 
                toast.ok(`✅ ${jobsData.length} offres !`); 
                load(); 
              } else if (attempts >= 12) { 
                clearInterval(poll); 
                toast.err('⚠ Aucune offre trouvée'); 
              }
            }, 5000);
          }}>🔍 Recherche d'offres</button>
          <button className="btn btn-danger btn-sm" onClick={delAll}>
            🗑 Vider {filter !== 'all' ? `(${filter})` : 'tout'}
          </button>
        </div>
      </div>
      <div className="filter-bar">
        {FILTERS.map(f => (
          <button key={f.k} className={`fbtn ${filter === f.k ? 'on' : ''}`} onClick={() => setFilter(f.k)}>
            {f.l} {jobs ? `(${jobs.filter(j => f.k === 'all' ? true : j.status === f.k).length})` : ''}
          </button>
        ))}
      </div>
      <div className="card">
        {!jobs ? (
          <div className="loading"><span className="spinner"></span>Chargement...</div>
        ) : filtered.length === 0 ? (
          <div className="empty"><div className="empty-ico">🔍</div><div>Lance une recherche d'offres</div></div>
        ) : filtered.map(j => (
          <div className="list-item" key={j.id}>
            <div className="list-item-row">
              <div className="list-item-title">{j.title}</div>
              <ScoreBar s={j.relevance_score} />
            </div>
            <div className="list-item-meta">
              <span className="badge b-dim">{j.platform}</span>
              <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>{j.location || '—'}</span>
              <span className={`badge ${j.status === 'shortlisted' ? 'b-mint' : j.status === 'ignored' ? 'b-danger' : 'b-dim'}`}>
                <span className="bdot"></span>{j.status}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 5, marginTop: 3 }}>
              {j.status === 'shortlisted' && (
                <button className="btn btn-mint btn-sm" onClick={() => gen(j.id)} disabled={gf[j.id]}>
                  {gf[j.id] ? <span className="spinner"></span> : '✨'} Candidater
                </button>
              )}
              <a href={j.url} target="_blank" rel="noreferrer" className="btn btn-ghost btn-sm">🔗 Voir</a>
              <button className="btn btn-danger btn-sm" onClick={e => { e.stopPropagation(); delOffer(j.id); }} disabled={df[j.id]}>
                {df[j.id] ? <span className="spinner"></span> : '🗑'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
