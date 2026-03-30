import { useState, useEffect } from 'react';
import { api } from '../api';
import { SBadge } from '../components/SBadge';
import { ScoreBar } from '../components/ScoreBar';

export function DashboardPage({ toast, user }) {
  const [apps, setApps] = useState(null);
  const [jobs, setJobs] = useState(null);
  const [gmail, setGmail] = useState(null);
  const [busy, setBusy] = useState({});
  const setB = (k, v) => setBusy(p => ({ ...p, [k]: v }));

  useEffect(() => {
    api('/api/applications/').then(r => r?.json()).then(d => d && setApps(d));
    api('/api/jobs/').then(r => r?.json()).then(d => d && setJobs(d));
    api('/api/auth/gmail/status').then(r => r?.json()).then(d => d && setGmail(d));
  }, []);

  const stats = { 
    total: apps?.length || 0, 
    sent: apps?.filter(a => a.status === 'sent').length || 0, 
    interviews: apps?.filter(a => ['interview_proposed', 'interview_confirmed'].includes(a.status)).length || 0, 
    pending: apps?.filter(a => ['pending_review', 'ready_to_send'].includes(a.status)).length || 0, 
    jobsTotal: jobs?.length || 0, 
    shortlisted: jobs?.filter(j => j.status === 'shortlisted').length || 0 
  };

  const action = async (key, path, method = 'POST', msg) => {
    setB(key, true);
    try {
      const r = await api(path, { method });
      if (!r) { toast.err('Erreur réseau'); return; }
      const d = await r.json();
      if (!r.ok) { toast.err(d.detail || 'Erreur serveur'); return; }
      if (key === 'scrape') {
        toast.info('🔍 Scraping en cours... (30-60 sec)');
        let attempts = 0;
        const poll = setInterval(async () => {
          attempts++;
          const rj = await api('/api/jobs/');
          const jobsData = await rj.json();
          if (jobsData && jobsData.length > 0) {
            clearInterval(poll);
            setB(key, false);
            toast.ok(`✅ ${jobsData.length} offres trouvées !`);
            setJobs(jobsData);
          } else if (attempts >= 12) {
            clearInterval(poll);
            setB(key, false);
            toast.err('⚠ Scraping terminé — aucune offre trouvée');
          }
        }, 5000);
        return;
      }
      toast.ok(msg || (d.scored ? `${d.scored} offres scorées` : 'Lancé !'));
    } catch { 
      toast.err('Erreur réseau — serveur inaccessible'); 
    } finally { 
      if (key !== 'scrape') setTimeout(() => setB(key, false), 2500); 
    }
  };

  return (
    <div>
      <div className="topbar">
        <div className="topbar-brand">Job<span>Agent</span></div>
        <button className="btn btn-mint btn-sm" disabled={busy.scrape} onClick={() => action('scrape', '/api/jobs/scrape', 'POST')}>
          {busy.scrape ? <span className="spinner"></span> : '🔍'}
        </button>
      </div>
      <div className="page-header">
        <div>
          <div className="page-title">Bonjour {user?.full_name?.split(' ')[0] || 'là'} 👋</div>
          <div className="page-sub">{gmail?.connected ? `✓ Gmail — ${gmail.email}` : '⚠ Gmail non connecté'}</div>
        </div>
        <div className="hdr-actions">
          <button className="btn btn-sec btn-sm" disabled={busy.cls} onClick={() => action('cls', '/api/applications/classify-responses', 'POST', 'Emails classifiés')}>
            {busy.cls ? <span className="spinner"></span> : '📬'} Classifier
          </button>
          <button className="btn btn-sec btn-sm" disabled={busy.score} onClick={() => action('score', '/api/jobs/score-all', 'POST')}>
            {busy.score ? <span className="spinner"></span> : '⚡'} Scorer
          </button>
          <button className="btn btn-mint btn-sm" disabled={busy.scrape} onClick={() => action('scrape', '/api/jobs/scrape', 'POST')}>
            {busy.scrape ? <><span className="spinner"></span> En cours...</> : '🔍 Scraper'}
          </button>
        </div>
      </div>
      <div className="stats-grid">
        {[
          { c: 'c-mint', ico: '📨', lbl: 'Candidatures', val: stats.total, sub: `${stats.sent} envoyées` }, 
          { c: 'c-cream', ico: '🎯', lbl: 'Entretiens', val: stats.interviews, sub: 'proposés' }, 
          { c: 'c-warn', ico: '⏳', lbl: 'À valider', val: stats.pending, sub: 'en attente' }, 
          { c: 'c-dim', ico: '📋', lbl: 'Offres', val: stats.jobsTotal, sub: `${stats.shortlisted} shortlistées` }
        ].map(s => (
          <div className={`stat-card ${s.c}`} key={s.lbl}>
            <span className="stat-ico">{s.ico}</span>
            <div className="stat-lbl">{s.lbl}</div>
            <div className="stat-val">{s.val}</div>
            <div className="stat-sub">{s.sub}</div>
          </div>
        ))}
      </div>
      <div className="card">
        <div className="card-hdr"><span className="card-ttl">Candidatures récentes</span></div>
        {!apps ? (
          <div className="loading"><span className="spinner"></span>Chargement...</div>
        ) : apps.length === 0 ? (
          <div className="empty"><div className="empty-ico">📭</div><div>Aucune candidature</div></div>
        ) : apps.slice(0, 5).map(a => (
          <div className="act-item" key={a.id}>
            <div className="act-dot" style={{ background: a.status === 'interview_proposed' ? 'var(--mint)' : a.status === 'refused' ? 'var(--danger)' : a.status === 'sent' ? 'var(--cream-dark)' : 'var(--warn)' }}></div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="act-ttl">{a.offer}</div>
              <div className="act-meta"><span>{a.company}</span><SBadge s={a.status} /></div>
            </div>
          </div>
        ))}
      </div>
      <div className="card">
        <div className="card-hdr"><span className="card-ttl">Meilleures offres</span></div>
        {!jobs ? (
          <div className="loading"><span className="spinner"></span>Chargement...</div>
        ) : jobs.filter(j => j.relevance_score).sort((a, b) => b.relevance_score - a.relevance_score).slice(0, 5).length === 0 ? (
          <div className="empty"><div className="empty-ico">🔍</div><div>Lance un scraping</div></div>
        ) : jobs.filter(j => j.relevance_score).sort((a, b) => b.relevance_score - a.relevance_score).slice(0, 5).map(j => (
          <div className="act-item" key={j.id}>
            <div className="act-dot" style={{ background: j.relevance_score >= 80 ? 'var(--mint)' : j.relevance_score >= 60 ? 'var(--warn)' : 'var(--danger)' }}></div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="act-ttl">{j.title}</div>
              <div className="act-meta"><span>{j.platform}</span><ScoreBar s={j.relevance_score} /></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
