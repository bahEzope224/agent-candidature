import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api';

// ── Messages contextuels ──────────────────────────────────────
const MESSAGES = {
  positive: {
    sent:      { emoji: '🚀', title: 'Candidature envoyée !', msg: 'Bien joué ! Chaque candidature est un pas de plus vers ton poste idéal. Continue comme ça !' },
    interview: { emoji: '🎯', title: 'Entretien décroché !', msg: 'Incroyable ! Ils ont vu quelque chose de special en toi. Prépare-toi bien, tu vas assurer !' },
    signed:    { emoji: '🏆', title: 'Contrat signé !', msg: 'FÉLICITATIONS ! Tu y es arrivé(e) ! C\'est le début d\'une belle aventure professionnelle. Tu le mérites vraiment !' },
  },
  negative: {
    ignored:   { emoji: '⏭️', title: 'Offre passée', msg: 'Sage décision. Mieux vaut attendre l\'opportunité qui te correspond vraiment. La prochaine sera la bonne !' },
    refused:   { emoji: '💪', title: 'Allez, on continue !', msg: 'Chaque refus te rapproche du "OUI" qui compte. Les plus grands ont tous traversé des refus. Tu es sur la bonne voie !' },
    no_response: { emoji: '🌱', title: 'Pas de réponse... Pas de problème !', msg: 'Leur silence ne dit rien de ta valeur. Le marché est compétitif mais ton talent, lui, est réel. La prochaine !' },
    refused_after_interview: { emoji: '🔥', title: 'Tu as passé les entretiens !', msg: 'C\'est déjà un exploit d\'arriver jusqu\'aux entretiens. Chaque entretien est un entraînement qui te rend encore plus fort(e) !' },
  }
};

// ── Tutoriel d'onboarding ─────────────────────────────────────
function SwipeTutorial({ onDismiss }) {
  const [step, setStep] = useState(0);
  const steps = [
    { dir: '→', color: '#2db87a', label: 'Swipe à droite', desc: 'Envoyer / Entretien / Signé' },
    { dir: '←', color: '#e05c5c', label: 'Swipe à gauche', desc: 'Ignorer / Refus' },
    { dir: '↑', color: '#8b949e', label: 'Swipe vers le haut', desc: 'Passer sans action' },
  ];

  useEffect(() => {
    if (step < steps.length) {
      const t = setTimeout(() => setStep(s => s + 1), 1200);
      return () => clearTimeout(t);
    } else {
      const t = setTimeout(onDismiss, 600);
      return () => clearTimeout(t);
    }
  }, [step]);

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'rgba(0,0,0,0.82)', display: 'flex',
      flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: 28, padding: 32,
    }}>
      <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.5)', letterSpacing: 2, fontFamily: 'DM Mono,monospace', textTransform: 'uppercase' }}>
        Comment ça marche
      </div>
      
      {/* Animated card demo */}
      <div style={{ position: 'relative', width: 200, height: 260, perspective: 600 }}>
        <div style={{
          position: 'absolute', inset: 0, background: 'var(--surface)',
          borderRadius: 20, border: '1px solid rgba(255,255,255,0.08)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8,
          transform: step < steps.length ? `translateX(${step === 0 ? '22px' : step === 1 ? '-22px' : '0'}) translateY(${step === 2 ? '-22px' : '0'}) rotate(${step === 0 ? '4deg' : step === 1 ? '-4deg' : '0deg'})` : 'none',
          transition: 'transform 0.5s cubic-bezier(.34,1.56,.64,1)',
          boxShadow: step < steps.length ? `0 0 0 2px ${steps[Math.min(step, steps.length-1)].color}40, 0 20px 60px rgba(0,0,0,0.4)` : 'none',
        }}>
          <div style={{ fontSize: 32 }}>🏢</div>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>Développeur F/H</div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>Acme Corp • Paris</div>
        </div>

        {/* Direction arrow overlay */}
        {step < steps.length && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 56, fontWeight: 900, color: steps[step].color,
            animation: 'pulse 0.6s ease-in-out',
            textShadow: `0 0 30px ${steps[step].color}80`,
          }}>
            {steps[step].dir}
          </div>
        )}
      </div>

      {/* Step descriptions */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', justifyContent: 'center' }}>
        {steps.map((s, i) => (
          <div key={i} style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
            opacity: step >= i ? 1 : 0.3, transition: 'opacity 0.4s',
          }}>
            <div style={{
              width: 44, height: 44, borderRadius: 14, background: s.color + '22',
              border: `2px solid ${step === i ? s.color : s.color + '44'}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 22, fontWeight: 900, color: s.color,
              transition: 'border-color 0.4s',
            }}>{s.dir}</div>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#fff', textAlign: 'center' }}>{s.label}</div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)', textAlign: 'center', maxWidth: 90 }}>{s.desc}</div>
          </div>
        ))}
      </div>

      <button onClick={onDismiss} style={{
        marginTop: 8, padding: '12px 32px', borderRadius: 14, border: 'none',
        background: 'rgba(255,255,255,0.1)', color: '#fff', fontSize: 13, cursor: 'pointer',
        backdropFilter: 'blur(8px)',
      }}>
        C'est compris, c'est parti ! 👍
      </button>
    </div>
  );
}

// ── Feedback overlay (positive / negative) ────────────────────
function SwipeFeedback({ msg, onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2600);
    return () => clearTimeout(t);
  }, []);

  const isPositive = !!MESSAGES.positive[msg?.key];
  const m = MESSAGES.positive[msg?.key] || MESSAGES.negative[msg?.key] || {};

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9000, display: 'flex',
      flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      background: isPositive ? 'rgba(45,184,122,0.12)' : 'rgba(224,92,92,0.10)',
      backdropFilter: 'blur(20px)',
      animation: 'fadeInScale 0.3s ease',
      gap: 16, padding: 32,
    }}>
      <div style={{ fontSize: 72, animation: 'bounceOnce 0.5s ease' }}>{m.emoji}</div>
      <div style={{
        fontSize: 22, fontWeight: 800, fontFamily: 'Syne,sans-serif',
        color: isPositive ? '#2db87a' : '#e05c5c', textAlign: 'center',
      }}>{m.title}</div>
      <div style={{ fontSize: 14, color: 'var(--text)', textAlign: 'center', maxWidth: 300, lineHeight: 1.6 }}>
        {m.msg}
      </div>
    </div>
  );
}

// ── Swipe Card ────────────────────────────────────────────────
function SwipeCard({ card, onSwipe, isTop }) {
  const ref = useRef(null);
  const startPos = useRef(null);
  const currentDelta = useRef({ x: 0, y: 0 });
  const [delta, setDelta] = useState({ x: 0, y: 0 });
  const [leaving, setLeaving] = useState(null); // 'right'|'left'|'up'
  const [showDetails, setShowDetails] = useState(false);

  const getActions = (status) => {
    if (['to_apply', 'pending_review', 'ready_to_send'].includes(status))
      return { right: { label: '✅ Envoyer', color: '#2db87a', key: 'sent' }, left: { label: '🗑 Ignorer', color: '#e05c5c', key: 'ignored' }, up: 'skip' };
    if (['sent', 'follow_up_needed', 'follow_up_sent', 'no_response'].includes(status))
      return { right: { label: '🎯 Entretien !', color: '#2db87a', key: 'interview' }, left: { label: '❌ Pas de réponse', color: '#e05c5c', key: 'no_response' }, up: 'skip' };
    if (['interview', 'interview_proposed'].includes(status))
      return { right: { label: '🏆 Contrat signé !', color: '#2db87a', key: 'signed' }, left: { label: '💔 Refus', color: '#e05c5c', key: 'refused_after_interview' }, up: 'skip' };
    return null;
  };

  const actions = getActions(card.status);
  const rotation = (delta.x / 220) * 18;
  const rightOpacity = Math.min(1, Math.max(0, delta.x / 80));
  const leftOpacity = Math.min(1, Math.max(0, -delta.x / 80));
  const upOpacity = Math.min(1, Math.max(0, -delta.y / 60));

  const onTouchStart = (e) => {
    startPos.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    currentDelta.current = { x: 0, y: 0 };
  };

  const onTouchMove = (e) => {
    if (!startPos.current) return;
    const dx = e.touches[0].clientX - startPos.current.x;
    const dy = e.touches[0].clientY - startPos.current.y;
    currentDelta.current = { x: dx, y: dy };
    setDelta({ x: dx, y: dy });
  };

  const onTouchEnd = () => {
    const { x, y } = currentDelta.current;
    const THRESHOLD = 90;
    if (x > THRESHOLD && actions?.right) { swipe('right'); }
    else if (x < -THRESHOLD && actions?.left) { swipe('left'); }
    else if (y < -THRESHOLD) { swipe('up'); }
    else { setDelta({ x: 0, y: 0 }); }
    startPos.current = null;
  };

  const swipe = (dir) => {
    setLeaving(dir);
    setTimeout(() => onSwipe(card, dir, actions), 350);
  };

  const transform = leaving === 'right'
    ? 'translateX(120vw) rotate(25deg)'
    : leaving === 'left'
    ? 'translateX(-120vw) rotate(-25deg)'
    : leaving === 'up'
    ? 'translateY(-120vh)'
    : `translateX(${delta.x}px) translateY(${delta.y * 0.4}px) rotate(${rotation}deg)`;

  const transition = leaving ? 'transform 0.35s cubic-bezier(.5,0,.5,1)' : delta.x !== 0 || delta.y !== 0 ? 'none' : 'transform 0.3s ease';

  return (
    <div
      ref={ref}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      style={{
        position: 'absolute', inset: 0,
        background: 'var(--surface)',
        borderRadius: 24,
        border: '1px solid var(--border)',
        boxShadow: isTop ? '0 20px 60px rgba(0,0,0,0.18)' : '0 8px 24px rgba(0,0,0,0.10)',
        transform,
        transition,
        display: 'flex', flexDirection: 'column',
        userSelect: 'none', WebkitUserSelect: 'none', WebkitTouchCallout: 'none',
        overflow: 'hidden',
        scale: isTop ? '1' : '0.96',
      }}
    >
      {/* Right indicator */}
      {actions?.right && (
        <div style={{
          position: 'absolute', top: 22, left: 22, zIndex: 10,
          background: actions.right.color, color: '#fff',
          borderRadius: 12, padding: '8px 16px', fontSize: 14, fontWeight: 800,
          transform: 'rotate(-12deg)', opacity: rightOpacity,
          boxShadow: `0 4px 16px ${actions.right.color}60`,
          transition: 'opacity 0.1s',
        }}>{actions.right.label}</div>
      )}

      {/* Left indicator */}
      {actions?.left && (
        <div style={{
          position: 'absolute', top: 22, right: 22, zIndex: 10,
          background: actions.left.color, color: '#fff',
          borderRadius: 12, padding: '8px 16px', fontSize: 14, fontWeight: 800,
          transform: 'rotate(12deg)', opacity: leftOpacity,
          boxShadow: `0 4px 16px ${actions.left.color}60`,
          transition: 'opacity 0.1s',
        }}>{actions.left.label}</div>
      )}

      {/* Up indicator */}
      <div style={{
        position: 'absolute', top: 22, left: '50%', transform: 'translateX(-50%)', zIndex: 10,
        background: '#555', color: '#fff',
        borderRadius: 12, padding: '6px 14px', fontSize: 12, fontWeight: 700,
        opacity: upOpacity, transition: 'opacity 0.1s',
      }}>⏭ Passer</div>

      {/* Card Content - Scrollable area */}
      <div 
        onTouchStart={e => e.stopPropagation()} // Ignore swipe when starting inside content
        style={{ 
          flex: 1, padding: '24px 22px 24px', display: 'flex', flexDirection: 'column', gap: 12,
          overflowY: 'auto', overflowX: 'hidden',
          WebkitOverflowScrolling: 'touch',
        }}
      >
        {/* Company logo placeholder */}
        <div style={{
          width: 56, height: 56, borderRadius: 16, background: 'var(--surface2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26,
          border: '1px solid var(--border)', flexShrink: 0,
        }}>🏢</div>

        <div>
          <div style={{ fontSize: 18, fontWeight: 800, fontFamily: 'Syne,sans-serif', color: 'var(--text)', lineHeight: 1.3, marginBottom: 4 }}>
            {card.offer}
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-dim)', fontWeight: 500 }}>{card.company}</div>
        </div>

        {card.location && (
          <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>📍 {card.location}</div>
        )}

        {card.confidence && (
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            background: card.confidence >= 0.8 ? 'rgba(45,184,122,0.12)' : 'rgba(224,160,80,0.12)',
            border: `1px solid ${card.confidence >= 0.8 ? 'rgba(45,184,122,0.3)' : 'rgba(224,160,80,0.3)'}`,
            borderRadius: 10, padding: '5px 12px', fontSize: 12, fontWeight: 700,
            color: card.confidence >= 0.8 ? '#2db87a' : '#e0a050',
            width: 'fit-content',
          }}>
            ⚡ Match {Math.round(card.confidence * 100)}%
          </div>
        )}

        {/* Status badge */}
        <div style={{
          fontSize: 11, padding: '4px 10px', borderRadius: 8,
          background: 'var(--surface2)', color: 'var(--text-dim)',
          width: 'fit-content', fontFamily: 'DM Mono,monospace',
        }}>
          {card.status?.replace(/_/g, ' ')}
        </div>

        {(card.status === 'follow_up_needed' ? card.followup_email_body : card.email_body) && (
          <div style={{
            fontSize: 11.5, color: 'var(--text-dim)', lineHeight: 1.6,
            display: showDetails ? 'block' : '-webkit-box',
            WebkitLineClamp: showDetails ? 'unset' : '3',
            WebkitBoxOrient: 'vertical',
            overflow: showDetails ? 'visible' : 'hidden',
            background: 'var(--surface2)', borderRadius: 10, padding: '10px 12px',
            marginTop: 4, transition: 'all 0.3s ease',
          }}>
            {card.status === 'follow_up_needed' ? card.followup_email_body : card.email_body}
          </div>
        )}

        {/* Détails action */}
        <button 
          onClick={(e) => { e.stopPropagation(); setShowDetails(!showDetails); }}
          style={{
            background: 'transparent', border: '1px solid var(--border)', borderRadius: 10,
            padding: '6px 12px', fontSize: 11, color: 'var(--text-dim)', cursor: 'pointer',
            marginTop: 'auto', width: 'fit-content', alignSelf: 'center'
          }}
        >
          {showDetails ? '🔼 Masquer détails' : '🔽 Voir mail & lettre'}
        </button>

        {showDetails && (
          <div style={{ 
            marginTop: 8, display: 'flex', flexDirection: 'column', gap: 10, 
            padding: '4px 0', borderTop: '1px dashed var(--border)',
            animation: 'fadeIn 0.2s ease'
          }}>
            {card.status === 'follow_up_needed' && card.followup_email_body ? (
              <button 
                onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(card.followup_email_body); alert('Mail de relance copié !'); }}
                style={{ padding: '8px', borderRadius: 8, border: 'none', background: 'var(--sec)', color: '#fff', fontSize: 11, fontWeight: 600 }}
              >📋 Copier la Relance</button>
            ) : card.email_body ? (
              <button 
                onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(card.email_body); alert('Email copié !'); }}
                style={{ padding: '8px', borderRadius: 8, border: 'none', background: 'var(--mint)', color: '#fff', fontSize: 11, fontWeight: 600 }}
              >📋 Copier l'Email</button>
            ) : (
              <div style={{ fontSize: 10.5, color: 'var(--text-dim)', padding: 4 }}>Mail non généré.</div>
            )}

            {card.cover_letter ? (
              <button 
                onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(card.cover_letter); alert('Lettre copiée !'); }}
                style={{ padding: '8px', borderRadius: 8, border: 'none', background: 'var(--sec)', color: '#fff', fontSize: 11, fontWeight: 600 }}
              >📄 Copier la Lettre</button>
            ) : (
              <div style={{ fontSize: 10.5, color: 'var(--text-dim)', padding: 4 }}>Lettre non générée.</div>
            )}

            {card.offer_url && (
              <a 
                href={card.offer_url} target="_blank" rel="noreferrer"
                style={{ 
                  padding: '8px', borderRadius: 8, textAlign: 'center', textDecoration: 'none',
                  background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', fontSize: 11, fontWeight: 600 
                }}
              >🔗 Voir l'offre & candidater</a>
            )}
          </div>
        )}
      </div>

      {/* Action hints at bottom */}
      {actions && (
        <div style={{
          padding: '16px 24px', display: 'flex', justifyContent: 'space-between',
          borderTop: '1px solid var(--border)',
          background: 'var(--surface2)',
        }}>
          <div style={{ fontSize: 12, color: '#e05c5c', fontWeight: 700 }}>
            ← {actions.left?.label}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>↑ Passer</div>
          <div style={{ fontSize: 12, color: '#2db87a', fontWeight: 700 }}>
            {actions.right?.label} →
          </div>
        </div>
      )}
    </div>
  );
}

// ── Status resolution ─────────────────────────────────────────
const STATUS_MAP = {
  sent:      { apiAction: '/confirm-sent',      statusFallback: 'sent' },
  interview: { apiAction: '/confirm-interview', statusFallback: 'interview' },
  signed:    { apiAction: null,                  statusFallback: 'offer' },
  ignored:   { apiAction: null,                  statusFallback: 'archived' },
  no_response: { apiAction: null,                statusFallback: 'no_response' },
  refused_after_interview: { apiAction: '/confirm-refused', statusFallback: 'refused' },
};

// ── Main SwipeMode Component ──────────────────────────────────
export function SwipeMode({ apps, onStatusChange, onClose, showClose = true }) {
  const [queue, setQueue] = useState(() => (apps || []).filter(a =>
    !['offer', 'refused', 'archived'].includes(a.status)
  ));
  const [feedback, setFeedback] = useState(null);
  const [showTutorial, setShowTutorial] = useState(() => {
    return !localStorage.getItem('swipe_tutorial_seen');
  });
  const [done, setDone] = useState(false);
  const [history, setHistory] = useState([]);

  const handleSwipe = useCallback(async (card, dir, actions) => {
    const actionKey = dir === 'right' ? actions?.right?.key
                    : dir === 'left'  ? actions?.left?.key
                    : null; // up = skip

    const originalStatus = card.status;

    if (actionKey && actionKey !== 'skip') {
      const mapped = STATUS_MAP[actionKey];
      if (mapped) {
        setHistory(h => [{ card, originalStatus, actionKey }, ...h].slice(0, 10)); // keep last 10
        if (mapped.apiAction) {
          await api(`/api/applications/${card.id}${mapped.apiAction}`, { method: 'PATCH' }).catch(() => {});
        } else {
          await api(`/api/applications/${card.id}/status?status=${mapped.statusFallback}`, { method: 'PATCH' }).catch(() => {});
        }
        onStatusChange?.(card.id, mapped.statusFallback);

        const isPositive = dir === 'right';
        const msgKey = isPositive ? MESSAGES.positive[actionKey] : MESSAGES.negative[actionKey];
        if (msgKey) setFeedback({ key: actionKey });
      }
    } else {
      // even for skipping, we can track history to allow undoing the "skip"
      setHistory(h => [{ card, originalStatus, actionKey: 'skip' }, ...h].slice(0, 10));
    }

    setQueue(q => {
      const next = q.slice(1);
      if (next.length === 0) setTimeout(() => setDone(true), 400);
      return next;
    });
  }, [onStatusChange, history]);

  const handleUndo = async () => {
    if (history.length === 0) return;
    const last = history[0];
    setHistory(h => h.slice(1));
    
    if (last.actionKey !== 'skip') {
      await api(`/api/applications/${last.card.id}/status?status=${last.originalStatus}`, { method: 'PATCH' }).catch(() => {});
      onStatusChange?.(last.card.id, last.originalStatus);
    }

    setQueue(q => [last.card, ...q]);
    setDone(false);
  };

  const dismissTutorial = () => {
    localStorage.setItem('swipe_tutorial_seen', '1');
    setShowTutorial(false);
  };

  if (showTutorial) return <SwipeTutorial onDismiss={dismissTutorial} />;

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0,
      bottom: showClose ? 0 : 72, // Hide close button means we are mobile, so leave room for nav
      zIndex: 50,
      background: 'var(--bg)',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* CSS animations */}
      <style>{`
        @keyframes fadeInScale { from { opacity:0; transform: scale(0.9); } to { opacity:1; transform: scale(1); } }
        @keyframes bounceOnce { 0%,100% { transform:scale(1); } 40% { transform:scale(1.3); } 70% { transform:scale(0.95); } }
        @keyframes pulse { 0%,100% { opacity:0.7; } 50% { opacity:1; } }
      `}</style>

      {/* Header */}
      <div style={{
        padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: '1px solid var(--border)', flexShrink: 0,
      }}>
        <div style={{ fontSize: 16, fontWeight: 800, fontFamily: 'Syne,sans-serif' }}>
          Mode Swipe 🃏
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--text-dim)', fontFamily: 'DM Mono,monospace' }}>
            {queue.length} restante{queue.length > 1 ? 's' : ''}
          </span>
          <button
            onClick={() => setShowTutorial(true)}
            style={{ padding: '6px 12px', borderRadius: 10, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-dim)', fontSize: 12, cursor: 'pointer' }}
          >? Aide</button>
          {showClose && (
            <button
              onClick={onClose}
              style={{ padding: '6px 14px', borderRadius: 10, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text)', fontSize: 13, cursor: 'pointer', fontWeight: 600 }}
            >✕</button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ height: 3, background: 'var(--surface2)', flexShrink: 0 }}>
        <div style={{
          height: '100%', background: 'var(--mint)',
          width: `${queue.length > 0 ? ((apps.length - queue.length) / apps.length) * 100 : 100}%`,
          transition: 'width 0.5s ease',
        }} />
      </div>

      {/* Cards stack */}
      <div style={{ flex: 1, position: 'relative', padding: '20px 20px 0', overflow: 'hidden' }}>
        {done || queue.length === 0 ? (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', gap: 16, padding: 32,
          }}>
            <div style={{ fontSize: 56 }}>🎉</div>
            <div style={{ fontSize: 22, fontWeight: 800, fontFamily: 'Syne,sans-serif', textAlign: 'center' }}>
              Toutes traitées !
            </div>
            <div style={{ fontSize: 14, color: 'var(--text-dim)', textAlign: 'center' }}>
              Tu as géré toutes tes candidatures. Excellent travail !
            </div>
            <button onClick={onClose} style={{
              padding: '14px 32px', borderRadius: 16, border: 'none',
              background: 'var(--mint)', color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer',
            }}>Retour au tableau 📋</button>
          </div>
        ) : (
          queue.slice(0, 3).map((card, i) => (
            <SwipeCard
              key={card.id}
              card={card}
              onSwipe={handleSwipe}
              isTop={i === 0}
            />
          )).reverse()
        )}
      </div>

      {/* Bottom action buttons (fallback for non-touch) */}
      {queue.length > 0 && !done && (() => {
        const topCard = queue[0];
        const getActions = (status) => {
          if (['to_apply', 'pending_review', 'ready_to_send'].includes(status))
            return { right: { label: '✅ Envoyer', key: 'sent' }, left: { label: '🗑 Ignorer', key: 'ignored' } };
          if (['sent', 'follow_up_needed', 'follow_up_sent', 'no_response'].includes(status))
            return { right: { label: '🎯 Entretien', key: 'interview' }, left: { label: '❌ Refus', key: 'no_response' } };
          if (['interview', 'interview_proposed'].includes(status))
            return { right: { label: '🏆 Signé !', key: 'signed' }, left: { label: '💔 Refus', key: 'refused_after_interview' } };
          return null;
        };
        const actions = getActions(topCard?.status);
        if (!actions) return null;
        return (
          <div style={{
            padding: '16px 24px 32px', display: 'grid', gridTemplateColumns: 'min-content 1fr min-content 1fr min-content', gap: 12,
            alignItems: 'center', flexShrink: 0,
          }}>
            <button
              onClick={() => handleSwipe(topCard, 'left', actions)}
              style={{
                width: 58, height: 58, borderRadius: '50%', border: '2px solid #e05c5c',
                background: 'rgba(224,92,92,0.1)', color: '#e05c5c', fontSize: 24, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'transform 0.1s',
              }}>✕</button>

            <button
              onClick={handleUndo}
              disabled={history.length === 0}
              style={{
                width: 44, height: 44, borderRadius: '50%', border: '1px solid var(--border)',
                background: 'var(--surface)', color: history.length > 0 ? 'var(--warn)' : 'var(--text-dim)',
                fontSize: 18, cursor: history.length > 0 ? 'pointer' : 'default', transition: 'all 0.2s',
                opacity: history.length > 0 ? 1 : 0.4,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>↺</button>

            <button
              onClick={() => handleSwipe(topCard, 'up', actions)}
              style={{
                width: 50, height: 50, borderRadius: '50%', border: '1px solid var(--border)',
                background: 'var(--surface)', color: 'var(--text-dim)', fontSize: 20, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>⏭</button>

            <div style={{ width: 44 }}></div> {/* Spacer to keep 5 slots balanced */}

            <button
              onClick={() => handleSwipe(topCard, 'right', actions)}
              style={{
                width: 58, height: 58, borderRadius: '50%', border: '2px solid #2db87a',
                background: 'rgba(45,184,122,0.12)', color: '#2db87a', fontSize: 24, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'transform 0.1s',
              }}>✓</button>
          </div>
        );
      })()}

      {/* Feedback overlay */}
      {feedback && <SwipeFeedback msg={feedback} onDone={() => setFeedback(null)} />}
    </div>
  );
}
