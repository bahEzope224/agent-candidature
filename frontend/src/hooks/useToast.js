import { useState } from 'react';

export function useToast() {
  const [items, setItems] = useState([]);
  const add = (msg, type = 'info') => {
    const id = Date.now();
    setItems(p => [...p, { id, msg, type }]);
    setTimeout(() => setItems(p => p.filter(t => t.id !== id)), 3500);
  };
  return { items, ok: m => add(m, 'success'), err: m => add(m, 'error'), info: m => add(m, 'info') };
}
