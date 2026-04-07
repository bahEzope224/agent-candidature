import { 
  DndContext, 
  MouseSensor,
  TouchSensor,
  useSensor, 
  useSensors,
  DragOverlay,
  closestCenter,
  useDroppable,
  defaultDropAnimationSideEffects
} from '@dnd-kit/core';
import { useState, useMemo, useCallback } from 'react';
import { KanbanCard } from './KanbanCard';

const COLUMNS = [
  { id: 'to_apply',  title: 'À postuler',     emoji: '📋', targetStatus: 'to_apply',  accepts: ['to_apply', 'pending_review', 'ready_to_send'] },
  { id: 'sent',      title: 'Candidaté',       emoji: '📨', targetStatus: 'sent',      accepts: ['sent', 'follow_up_needed', 'follow_up_sent', 'no_response'] },
  { id: 'interview', title: 'Entretien',       emoji: '🎯', targetStatus: 'interview', accepts: ['interview', 'interview_proposed'] },
  { id: 'signed',    title: 'Contrat Signé',   emoji: '✅', targetStatus: 'offer',     accepts: ['offer'] },
  { id: 'refused',   title: 'Refus',            emoji: '❌', targetStatus: 'refused',   accepts: ['refused', 'archived'] },
];


function DroppableColumn({ col, items, onDetails }) {
  const { setNodeRef, isOver } = useDroppable({
    id: col.id,
    data: { type: 'column', columnId: col.id }
  });

  return (
    <div className="kanban-col" data-col={col.id}>
      <div className="kanban-col-hdr">
        <span className="kanban-col-ttl">{col.emoji} {col.title}</span>
        <span className="kanban-count">{items.length}</span>
      </div>
      <div 
        ref={setNodeRef}
        className={`kanban-list ${isOver ? 'over' : ''}`}
      >
        {items.map(item => (
          <KanbanCard 
            key={item.id} 
            item={item} 
            onClick={() => onDetails(item.id)}
          />
        ))}
        {items.length === 0 && (
          <div style={{ 
            padding: '24px 16px', 
            textAlign: 'center', 
            fontSize: 11, 
            color: 'var(--text-dim)',
            border: isOver ? '2px dashed var(--mint)' : '2px dashed var(--border)',
            borderRadius: 10,
            transition: 'all 0.2s'
          }}>
            {isOver ? 'Déposer ici ✓' : 'Glisser ici'}
          </div>
        )}
      </div>
    </div>
  );
}

export function KanbanBoard({ apps, onStatusChange, onDetails }) {
  const [activeId, setActiveId] = useState(null);

  const sensors = useSensors(
    useSensor(MouseSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(TouchSensor, {
      activationConstraint: {
        delay: 250,
        tolerance: 5,
      },
    })
  );

  const columnsData = useMemo(() => {
    return COLUMNS.map(col => ({
      ...col,
      items: apps.filter(a => col.accepts.includes(a.status))
    }));
  }, [apps]);

  const activeItem = useMemo(() => 
    apps.find(a => a.id === activeId), 
  [apps, activeId]);

  // Find which column a card belongs to
  const findColumnForCard = useCallback((cardId) => {
    for (const col of columnsData) {
      if (col.items.find(i => i.id === cardId)) {
        return col;
      }
    }
    return null;
  }, [columnsData]);

  const handleDragStart = (event) => {
    setActiveId(event.active.id);
  };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over || !active) return;

    const draggedCardId = active.id;
    const draggedCard = apps.find(a => a.id === draggedCardId);
    if (!draggedCard) return;

    // Find source column
    const sourceCol = findColumnForCard(draggedCardId);

    // Find target column — either dropped on a column or on a card inside a column
    let targetCol = null;

    // Check if dropped directly on a column droppable
    if (over.data.current?.type === 'column') {
      targetCol = COLUMNS.find(c => c.id === over.data.current.columnId);
    } else {
      // Dropped on a card — find the column that card belongs to
      const overCard = apps.find(a => a.id === over.id);
      if (overCard) {
        targetCol = COLUMNS.find(col => col.accepts.includes(overCard.status));
      }
    }

    if (!targetCol || !sourceCol) return;

    // If same column, do nothing
    if (sourceCol.id === targetCol.id) return;

    // Update status to target column's target status
    onStatusChange(draggedCardId, targetCol.targetStatus);
  };

  const dropAnimation = {
    sideEffects: defaultDropAnimationSideEffects({
      styles: { active: { opacity: '0.4' } },
    }),
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="kanban-container">
        {columnsData.map(col => (
          <DroppableColumn
            key={col.id}
            col={col}
            items={col.items}
            onDetails={onDetails}
          />
        ))}
      </div>

      <DragOverlay dropAnimation={dropAnimation}>
        {activeId && activeItem ? (
          <KanbanCard item={activeItem} isOverlay />
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
