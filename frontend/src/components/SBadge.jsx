export const ST = {
  to_apply: { l: '📋 À candidater', c: 'b-warn' },
  sent: { l: '📨 Envoyée', c: 'b-mint' },
  follow_up_needed: { l: '🔔 À relancer', c: 'b-warn' },
  follow_up_sent: { l: '🔁 Relancée', c: 'b-cream' },
  no_response: { l: '😶 Sans réponse', c: 'b-dim' },
  interview: { l: '🎯 Entretien', c: 'b-mint' },
  refused: { l: '✕ Refus', c: 'b-danger' },
  archived: { l: 'Archivée', c: 'b-dim' },
  pending_review: { l: 'À valider', c: 'b-warn' },
  ready_to_send: { l: 'Prête', c: 'b-warn' },
  response_received: { l: 'Réponse', c: 'b-mint' },
  interview_proposed: { l: '🎯 Entretien', c: 'b-mint' },
};

export function SBadge({ s }) {
  const d = ST[s] || { l: s, c: 'b-dim' };
  return <span className={`badge ${d.c}`}><span className="bdot"></span>{d.l}</span>;
}
