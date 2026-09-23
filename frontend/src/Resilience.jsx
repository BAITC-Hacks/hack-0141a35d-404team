import React,{useState} from 'react';
import {featureText} from './features-i18n';

export default function Resilience({data,lang,onNavigate}){
 const t=featureText[lang],max=Math.min(100,data.nodes.length);
 const [n,setN]=useState(Math.min(5,max)),[result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function simulate(){
  setBusy(true);setError('');
  try{const r=await fetch('/api/resilience',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dataset_id:data.dataset_id,n:Number(n)})});
   const j=await r.json();if(!r.ok)throw new Error(t.error);setResult(j);
  }catch(e){setError(e.message);}finally{setBusy(false);}
 }
 return <details className="help resilience"><summary>{t.resilience}</summary>
  <p>{t.scope}</p><div className="simulation-controls"><input type="number" aria-label={t.removeCount} min="0" max={max} value={n} onChange={e=>setN(e.target.value)}/><button disabled={busy||n===''||!Number.isInteger(Number(n))||Number(n)<0||Number(n)>max} onClick={simulate}>{busy?'…':t.simulate}</button></div>
  {error&&<p role="alert">{error}</p>}{result&&<><p>{t.removed}: {result.removed_gids.length}</p><table><thead><tr><th></th><th>{t.before}</th><th>{t.after}</th></tr></thead><tbody>{['nodes','edges','components','largest_component','isolated'].map(k=><tr key={k}><td>{k==='largest_component'?t.largest:t[k]}</td><td>{result.before[k]}</td><td>{result.after[k]}</td></tr>)}</tbody></table><details><summary>{t.removed}</summary>{result.removed_gids.map(gid=><button key={gid} className="citation" onClick={()=>onNavigate(gid)}>{gid}</button>)}</details></>}
 </details>;
}
