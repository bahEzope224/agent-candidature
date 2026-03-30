import { useDraggable } from '@dnd-kit/core';
import { SBadge } from './SBadge';

export function KanbanCard({ item, onClick, isOverlay }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    isDragging
  } = useDraggable({ 
    id: item.id,
    data: {
      type: 'card',
      item
    }
  });

  const style = transform ? {
    transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
  } : undefined;

  return (
    <div
      ref={setNodeRef}
      style={{
        ...style,
        opacity: isDragging ? 0.3 : 1,
        ...(isOverlay ? { boxShadow: '0 8px 24px rgba(0,0,0,0.15)', transform: 'rotate(2deg)' } : {})
      }}
      className={`k-card ${isDragging ? 'dragging' : ''}`}
      {...attributes}
      {...listeners}
      onPointerUp={(e) => {
        // Only trigger click if not dragged
        if (!isDragging && !transform) {
          onClick?.();
        }
      }}
    >
      <div className="k-card-ttl">{item.offer}</div>
      <div className="k-card-corp">{item.company}</div>
      <div className="k-card-foot">
        <SBadge s={item.status} />
        <span className="k-card-date">
          {new Date(item.created_at).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}
        </span>
      </div>
    </div>
  );
}
