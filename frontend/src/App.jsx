import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { clearAuth, getUser, setUser, api } from './api';
import { useToast } from './hooks/useToast';
import { Toasts } from './components/Toasts';

import { AuthPage } from './pages/AuthPage';
import { DashboardPage } from './pages/DashboardPage';
import { ApplicationsPage } from './pages/ApplicationsPage';
import { OffersPage } from './pages/OffersPage';
import { ProfilePage } from './pages/ProfilePage';
import { AdminPanel } from './pages/AdminPanel';
import { Privacy } from './pages/legal/Privacy';
import { Terms } from './pages/legal/Terms';
import { Legal } from './pages/legal/Legal';

function ProtectedLayout() {
  const [user, setUserState] = useState(getUser());
  const [apps, setApps] = useState(null);
  const [showMenu, setShowMenu] = useState(false);
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => { 
    if (!user) {
      navigate('/');
    } else {
      api('/api/applications/').then(r => r?.json()).then(d => d && setApps(d)); 
    }
  }, [user, navigate]);

  if (!user) return null;

  const pendingCount = apps?.filter(a => ['pending_review', 'ready_to_send', 'to_apply', 'follow_up_needed'].includes(a.status)).length || 0;
  const interviewCount = apps?.filter(a => a.status === 'interview').length || 0;
  const initials = ((user.full_name || user.email || '?').split(' ').map(w => w[0] || '').join('').slice(0, 2).toUpperCase());
  
  const NAV = [
    { k: '/dashboard', ico: '◈', l: 'Home' }, 
    { k: '/applications', ico: '📨', l: 'Candidats', b: pendingCount || null }, 
    { k: '/offers', ico: '🔍', l: 'Offres' }, 
    { k: '/profile', ico: '👤', l: 'Profil' }
  ];

  const handleLogout = () => {
    clearAuth();
    setUserState(null);
    navigate('/');
  };

  return (
    <div className="layout">
      <aside className="sidebar-desktop" id="sidebar">
        <div className="sb-brand"><div className="sb-logo">Job<span>Agent</span></div><div className="sb-version">v1.0 — MVP</div></div>
        <div className="sb-user">
          <div className="sb-avatar">{initials}</div>
          <div><div className="sb-uname">{user.full_name || 'Utilisateur'}</div><div className="sb-uemail">{user.email}</div></div>
        </div>
        <nav className="sb-nav">
          <div className="sb-section">Navigation</div>
          {NAV.map(n => (
            <div key={n.k} className={`nav-item ${location.pathname === n.k ? 'active' : ''}`} onClick={() => navigate(n.k)}>
              <span className="nav-icon">{n.ico}</span>{n.l}
              {n.b ? <span className="nav-badge">{n.b}</span> : null}
            </div>
          ))}
          {interviewCount > 0 && (
            <div style={{ background: 'rgba(45,184,122,0.1)', border: '1px solid rgba(45,184,122,0.2)', borderRadius: 8, padding: '9px 11px', margin: '11px 2px 0' }}>
              <div style={{ fontSize: 11.5, color: 'var(--mint)', fontWeight: 600, marginBottom: 1 }}>🎯 {interviewCount} entretien(s)</div>
              <div style={{ fontSize: 10.5, color: 'rgba(45,184,122,0.6)' }}>Félicitations !</div>
            </div>
          )}
        </nav>
        <div className="sb-bottom">
          <button className="btn-logout" onClick={handleLogout}>↩ Se déconnecter</button>
        </div>
      </aside>

      <main className="main">
        <Routes>
          <Route path="/dashboard" element={<DashboardPage toast={toast} user={user} />} />
          <Route path="/applications" element={<ApplicationsPage toast={toast} />} />
          <Route path="/offers" element={<OffersPage toast={toast} />} />
          <Route path="/profile" element={<ProfilePage toast={toast} user={user} />} />
        </Routes>
      </main>

      <nav className="bottom-nav">
        {NAV.map(n => (
          <button key={n.k} className={`bn-item ${location.pathname === n.k ? 'active' : ''}`} onClick={() => navigate(n.k)}>
            {n.b ? <span className="bn-badge">{n.b}</span> : null}
            <span className="bn-ico">{n.ico}</span>
            <span className="bn-lbl">{n.l}</span>
          </button>
        ))}
        <button className="bn-item" onClick={() => setShowMenu(true)}>
          <span className="bn-ico" style={{ width: 22, height: 22, borderRadius: '50%', background: 'var(--mint)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontFamily: 'Syne,sans-serif', fontWeight: 700, fontSize: 10 }}>{initials}</span>
          <span className="bn-lbl">Moi</span>
        </button>
      </nav>

      {showMenu && (
        <div className="modal-ov" onClick={() => setShowMenu(false)}>
          <div className="user-menu" onClick={e => e.stopPropagation()}>
            <div className="modal-handle"></div>
            <div className="p-avatar" style={{ margin: '0 auto 9px' }}>{initials}</div>
            <div className="user-menu-name">{user.full_name || 'Utilisateur'}</div>
            <div className="user-menu-email">{user.email}</div>
            <div className="user-menu-item" onClick={() => { navigate('/profile'); setShowMenu(false); }}><span>👤</span>Mon profil</div>
            <div className="user-menu-item" style={{ color: 'var(--danger)' }} onClick={handleLogout}><span>↩</span>Se déconnecter</div>
          </div>
        </div>
      )}
      <Toasts items={toast.items} />
    </div>
  );
}

function MainApp() {
  const navigate = useNavigate();
  return (
    <Routes>
      <Route path="/" element={<AuthPage onLogin={(user) => { navigate('/dashboard'); }} />} />
      <Route path="/admin" element={<AdminPanel />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/legal" element={<Legal />} />
      <Route path="/*" element={<ProtectedLayout />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <MainApp />
    </BrowserRouter>
  );
}
