import { useState, useEffect } from 'react';
import { api } from '../api';
import { ScoreBar } from '../components/ScoreBar';

export function OffersPage({ toast }) {
  const [jobs, setJobs] = useState(null);
  const [filter, setFilter] = useState('shortlisted');
  const [scoring, setScoring] = useState(false);
  const [gf, setGf] = useState({});
  const [df, setDf] = useState({});
  const [copied, setCopied] = useState({});

  const load = () => api('/api/jobs/').then(r => r?.json()).then(d => d && setJobs(d));
  useEffect(() => { load(); }, []);

  const allowedStatuses = ['shortlisted', 'ignored'];
  const filtered = jobs
    ? jobs.filter(j => allowedStatuses.includes(j.status) && j.status === filter)
    : [];

  const scoreAll = async () => {
    setScoring(true);
    try { 
      const r = await api('/api/jobs/score-all', { method: 'POST' }); 
      const d = await r.json(); 
      toast.ok(`${d.scored} offres scorées`); 
      load(); 
      setFilter('shortlisted');
    } catch { 
      toast.err('Erreur'); 
    } finally { 
      setScoring(false); 
    }
  };

  const handleApply = async job => {
    const pendingWindow = job.url ? window.open(job.url, '_blank') : null;
    setGf(p => ({ ...p, [job.id]: true }));
    try { 
      const r = await api(`/api/applications/generate/${job.id}`, { method: 'POST' });
      const d = await r.json();
      if (!r.ok) { 
        toast.err(d.detail || 'Erreur de génération'); 
        return;
      }
      await load();
      const toCopy = `${d.email_subject || ''}\n\n${d.email_body || ''}\n\n${d.cover_letter || ''}`;
      if (navigator.clipboard && toCopy.trim()) {
        await navigator.clipboard.writeText(toCopy);
        setCopied(p => ({ ...p, [job.id]: true }));
        setTimeout(() => setCopied(p => ({ ...p, [job.id]: false })), 2200);
      }
      toast.info('Lettre + mail copiés, poste en attente de confirmation.');
      if (!pendingWindow && job.url) {
        window.open(job.url, '_blank');
      }
    } catch { 
      toast.err('Erreur'); 
    } finally { 
      setGf(p => ({ ...p, [job.id]: false })); 
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
    const label = filter === 'shortlisted' ? 'shortlistées' : 'ignorées';
    // eslint-disable-next-line no-restricted-globals
    if (!confirm(`Supprimer toutes les offres (${label}) ?`)) return;
    try {
      await api(`/api/jobs/?status=${filter}`, { method: 'DELETE' });
      toast.ok('Offres supprimées');
      load();
    } catch { 
      toast.err('Erreur'); 
    }
  };

  const FILTERS = [
    { k: 'shortlisted', l: '⭐ Offres shortlistées' },
    { k: 'ignored', l: '✕ Offres ignorées' }
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
          <div className="page-title">Focus shortlistées</div>
          <div className="page-sub">{jobs ? `${jobs.filter(j => allowedStatuses.includes(j.status)).length} opportunités suivies` : ''}</div>
          <div className="page-note" style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 6 }}>
            Après chaque recherche/match, cette page n’affiche que les offres shortlistées ou déjà ignorées. Utilise les filtres pour naviguer entre les deux vues.
          </div>
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
              setFilter('shortlisted');
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
            {f.l} {jobs ? `(${jobs.filter(j => j.status === f.k).length})` : ''}
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
            <div style={{ display: 'flex', gap: 5, marginTop: 3, alignItems: 'center' }}>
              {j.status === 'shortlisted' && (
                <>
                  <button className="btn btn-mint btn-sm" onClick={() => handleApply(j)} disabled={gf[j.id]}>
                    {gf[j.id] ? <span className="spinner"></span> : '✨'} Ouvrir & Candidater 
                  </button>
                  {copied[j.id] && (
                    <span className="badge b-mint" style={{ fontSize: 11 }}>
                      📋 Lettre + Mail copiés
                    </span>
                  )}
                </>
              )}
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
