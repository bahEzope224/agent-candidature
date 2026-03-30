import { useState } from 'react';

export function TagInput({ values = [], onChange, placeholder }) {
  const [inp, setInp] = useState('');
  const add = () => { 
    const v = inp.trim(); 
    if (v && !values.includes(v)) onChange([...values, v]); 
    setInp(''); 
  };
  
  return (
    <div className="tags-wrap">
      {values.map((v, i) => (
        <span className="tag" key={i}>
          {v}
          <span className="tag-x" onClick={() => onChange(values.filter((_, j) => j !== i))}>×</span>
        </span>
      ))}
      <input 
        className="tag-inp" 
        value={inp} 
        onChange={e => setInp(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add(); } }}
        placeholder={values.length === 0 ? placeholder : 'Ajouter...'} 
      />
    </div>
  );
}
