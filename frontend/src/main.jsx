import React,{useState,useMemo,useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import Graph from './Graph.jsx';
import {visibleGraph} from './graph.js';
import {dictionaries,roles,colors,evidence} from './i18n';
import './style.css';

function App(){
 const [lang,setLang]=useState(()=>localStorage.getItem('aml-language')==='ru'?'ru':'en');
 const [data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [folder,setFolder]=useState('entryset'),[query,setQuery]=useState(''),[selected,setSelected]=useState(null),[hovered,setHovered]=useState(null);
 const [mode,setMode]=useState('all'),[cluster,setCluster]=useState('all'),[color,setColor]=useState('role');
 const t=dictionaries[lang];
 useEffect(()=>{localStorage.setItem('aml-language',lang);document.documentElement.lang=lang;},[lang]);
 const graph=useMemo(()=>data?visibleGraph(data,selected,mode,cluster):null,[data,selected,mode,cluster]);
 const ranked=useMemo(()=>data?[...data.nodes].sort((a,b)=>b.priority_score-a.priority_score||b.role_score-a.role_score||a.gid.localeCompare(b.gid)):[],[data]);
 const inspected=hovered||data?.nodes.find(n=>n.gid===selected);
 async function run(){
  setBusy(true);setError('');
  try{
   const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({input_dir:folder})});
   const result=await response.json();if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:t.failed);
   setData(result);setSelected(null);setHovered(null);setCluster('all');setMode('all');setQuery('');
  }catch(e){setError(e instanceof TypeError?t.networkError:e.message);}finally{setBusy(false);}
 }
 function focus(id){setSelected(id);setQuery(id);setCluster('all');setMode('neighborhood');setHovered(null);setError('');}
 function search(e){e.preventDefault();if(data?.nodes.some(n=>n.gid===query.trim()))focus(query.trim());else setError(t.missing);}
 return <div className="app">
  <header><div className="brand"><span className="brand-icon">◈</span><div><b>AML GRAPH</b><small>{t.subtitle}</small></div></div><select aria-label={t.language} value={lang} onChange={e=>setLang(e.target.value)}><option value="en">English</option><option value="ru">Русский</option></select></header>
  <div className="workspace"><aside>
   <label>{t.folder}<input value={folder} onChange={e=>setFolder(e.target.value)} spellCheck="false"/></label>
   <button className="primary" onClick={run} disabled={busy}>{busy?t.running:t.run}<span>↗</span></button>
   <div className="divider"/><h2>{t.top}</h2>
   <div className="rank-list">{ranked.slice(0,20).map((n,i)=><button key={n.gid} className={'rank '+(selected===n.gid?'active':'')} onClick={()=>focus(n.gid)}><span className="rank-number">{String(i+1).padStart(2,'0')}</span><span><code>{n.gid}</code><small style={{color:colors[n.role]}}>{roles[lang][n.role]}</small></span><span>{n.priority_score.toFixed(2)}</span></button>)}</div>
   {data&&<div className="downloads"><h2>{t.exports}</h2>{['nodes_roles','clusters','top_nodes'].map(name=><a key={name} href={'/api/exports/'+name+'.csv'} download>{name}.csv <span>↓</span></a>)}</div>}
  </aside><main>
   <div className="title-row"><div><span className="eyebrow">AML / GRAPH EXPLORER</span><h1>{t.title}</h1></div>{data&&<div className="stats"><span><b>{data.report.n_nodes.toLocaleString()}</b>{t.nodes}</span><span><b>{data.report.n_edges.toLocaleString()}</b>{t.edges}</span><span><b>{data.report.n_seed}</b>{t.seeds}</span><span><b>{data.elapsed_seconds}{t.seconds}</b>{t.time}</span></div>}</div>
   {error&&<div className="error" role="alert">{error}</div>}
   <div className="toolbar"><form onSubmit={search}><input aria-label={t.search} placeholder={t.search} value={query} onChange={e=>setQuery(e.target.value)} inputMode="numeric"/><button disabled={!data}>{t.find}</button></form>
    <select aria-label={t.cluster} value={cluster} onChange={e=>{setCluster(e.target.value);setMode('all');setHovered(null);setSelected(null);}}><option value="all">{t.all}</option>{data?.clusters.map(c=><option key={c.cluster_id} value={c.cluster_id}>{t.cluster} {c.cluster_id} · {c.n_nodes}</option>)}</select>
    <select aria-label={t.color} value={color} onChange={e=>setColor(e.target.value)}><option value="role">{t.role}</option><option value="cluster">{t.cluster}</option></select>
    <button onClick={()=>{setMode('all');setCluster('all');setSelected(null);setHovered(null);}}>{t.overview}</button>
   </div>
   <section className="graph-workspace" aria-label={t.title}>
    {graph?<Graph graph={graph} selected={selected} onSelect={id=>{setSelected(id);setQuery(id);}} onHover={setHovered} color={color} t={t}/>:<div className="empty"><span>◈</span><h2>{t.title}</h2><p>{t.empty}</p></div>}
    {graph&&<div className="graph-meta">{mode==='all'?t.overview:t.neighborhood} · {graph.nodes.length} {t.nodes.toLowerCase()} · {graph.edges.length} {t.edges.toLowerCase()}</div>}
    <div className="legend">{color==='role'?Object.entries(colors).map(([role,c])=><span key={role}><i style={{background:c}}/>{roles[lang][role]}</span>):<span>{t.cluster}</span>}</div>
    {data&&<article className="evidence" aria-live="polite"><div className="eyebrow">{t.details}</div>{inspected?<><h3><i style={{background:colors[inspected.role]}}/>{roles[lang][inspected.role]}</h3><code>{inspected.gid}</code><p>{evidence(inspected,lang)}</p><dl><div><dt>{t.priority}</dt><dd>{inspected.priority_score.toFixed(2)}</dd></div><div><dt>{t.depth}</dt><dd>{inspected.depth}</dd></div><div><dt>{t.cluster}</dt><dd>{inspected.component_id}</dd></div></dl><div className="flow">{t.incoming}: {inspected.in_amount.toLocaleString(lang)} KZT<br/>{t.outgoing}: {inspected.out_amount.toLocaleString(lang)} KZT</div>{inspected.is_seed&&<p className="warning">{t.seedWarning}</p>}{inspected.is_depth4_boundary&&<p className="warning">{t.boundaryWarning}</p>}</>:<p>{t.hover}</p>}</article>}
   </section><footer><span>{t.hint}</span><span>{t.review}</span></footer>
  </main></div>
 </div>;
}
createRoot(document.getElementById('root')).render(<App/>);
