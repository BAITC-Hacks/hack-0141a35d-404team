import React,{useEffect,useState} from 'react';
import {dictionaries,roles,colors,evidence} from './i18n';
import {featureText} from './features-i18n';

export default function NodeCard({data,node,selected,lang,onNavigate}){
 const t=dictionaries[lang],f=featureText[lang];
 const [card,setCard]=useState(null),[error,setError]=useState('');
 useEffect(()=>{
  setCard(null);setError('');if(!selected)return;
  const controller=new AbortController();
  fetch(`/api/nodes/${selected}/card?dataset_id=${data.dataset_id}`,{signal:controller.signal})
   .then(async r=>{const j=await r.json();if(!r.ok)throw new Error(f.error);return j;})
   .then(setCard).catch(e=>{if(e.name!=='AbortError')setError(e.message);});
  return()=>controller.abort();
 },[selected,data.dataset_id]);
 const signals=card&&node&&card.node.gid===node.gid?card.insights:null;
 const links=gids=>gids.map((gid,i)=><React.Fragment key={i}>{i>0?' → ':''}<button className="citation" onClick={()=>onNavigate(gid)}>{gid}</button></React.Fragment>);
 function download(){
  const text=[node.gid,roles[lang][node.role],evidence(node,lang),
   `${t.priority}: ${node.priority_score} · ${t.cluster}: ${node.cluster_id} · ${t.depth}: ${node.depth}`,
   `${t.incoming}: ${node.in_amount} KZT · ${t.outgoing}: ${node.out_amount} KZT`,
   `${f.senders}: ${node.n_senders} · ${f.receivers}: ${node.n_receivers}`,
   ...(node.is_seed?[t.seedWarning]:[]),...(node.is_depth4_boundary?[t.boundaryWarning]:[]),
   ...signals.signals.map(s=>f[s]),f.timing,...signals.requests.map(r=>f[r]),JSON.stringify(signals,null,2)].join('\n');
  const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download=`node-${node.gid}.txt`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 return <article className="evidence node-card" aria-label={t.details}>
  <div className="eyebrow">{t.details}</div>{node?<>
   <h3><i style={{background:colors[node.role]}}/>{roles[lang][node.role]}</h3><code>{node.gid}</code>
   <p>{evidence(node,lang)}</p>
   <dl><div><dt>{t.priority}</dt><dd>{node.priority_score.toFixed(4)}</dd></div><div><dt>{t.depth}</dt><dd>{node.depth}</dd></div><div><dt>{t.cluster}</dt><dd>{node.cluster_id}</dd></div></dl>
   <div className="flow">{t.incoming}: {node.in_amount.toLocaleString(lang)} KZT<br/>{t.outgoing}: {node.out_amount.toLocaleString(lang)} KZT<br/>{f.senders}: {node.n_senders} · {f.receivers}: {node.n_receivers}</div>
   {node.is_seed&&<p className="warning">{t.seedWarning}</p>}{node.is_depth4_boundary&&<p className="warning">{t.boundaryWarning}</p>}
   {error&&node.gid===selected&&<p role="alert">{error}</p>}
   {signals?<><div className="signal-tags">{signals.signals.length?signals.signals.map(s=><span key={s}>{f[s]}</span>):<span>{f.none}</span>}</div>
    <details key={node.gid} className="node-patterns"><summary>{f.patternDetails}</summary>
     <h4>{f.temporal}</h4><p>{signals.matched_48h_kzt.toLocaleString(lang)} KZT</p><small>{f.timing}</small>
     <h4>{f.burst}</h4><p>{signals.burst_days.join(', ')||f.none}</p>
     <h4>{f.synchronous}</h4>{signals.synchronous_days.length?signals.synchronous_days.map(s=><p key={s.date}>{s.date} · {f.senders}: {s.n_senders}</p>):<p>{f.none}</p>}
     <h4>{f.repeats}</h4>{signals.repeated_amount_groups.length?signals.repeated_amount_groups.map((s,i)=><p key={i}>{s.date} · {s.count} × {s.amount_kzt.toLocaleString(lang)} KZT · {links([s.dst])}</p>):<p>{f.none}</p>}
     <h4>{f.outlier}</h4><p>{signals.depth_volume_threshold_kzt?.toLocaleString(lang)??'—'} KZT · {f.peerCount}: {signals.depth_peer_count}</p>
     <h4>{f.routes}</h4>{signals.routes.length?signals.routes.map((r,i)=><p key={i}>{links(r.gids)} · {r.matching_events} {f.event}</p>):<p>{f.none}</p>}
     <h4>{f.cycles}</h4>{signals.cycles.length?signals.cycles.map((r,i)=><p key={i}>{links([...r.gids,r.gids[0]])}</p>):<p>{f.none}</p>}<small>{f.cycleCaution}</small>
    </details>
    <details className="data-requests"><summary>{f.requests}</summary><ul>{signals.requests.map(r=><li key={r}>{f[r]}</li>)}</ul></details>
    <button className="card-download" onClick={download}>{f.download} ↓</button>
   </>:<p className="card-hint">{f.select}</p>}
  </>:<p>{t.hover}</p>}
 </article>;
}
