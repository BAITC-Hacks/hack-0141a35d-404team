import React,{useState,useMemo,useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import Graph from './Graph.jsx';
import Chat from './Chat.jsx';
import NodeCard from './NodeCard.jsx';
import Resilience from './Resilience.jsx';
import {visibleGraph} from './graph.js';
import {dictionaries,roles,colors} from './i18n';
import {featureText} from './features-i18n';
import './style.css';
import './refinements.css';
import './features.css';

function App(){
 const [lang,setLang]=useState(()=>localStorage.getItem('aml-language')==='ru'?'ru':'en');
 const [data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [folder,setFolder]=useState('entryset'),[query,setQuery]=useState(''),[selected,setSelected]=useState(null),[hovered,setHovered]=useState(null);
 const [mode,setMode]=useState('all'),[cluster,setCluster]=useState('all'),[color,setColor]=useState('role');
 const [history,setHistory]=useState([]),[origin,setOrigin]=useState(null),[hops,setHops]=useState(1),[direction,setDirection]=useState('both');
 const previous=history.at(-1)||null;
 const t=dictionaries[lang];
 useEffect(()=>{localStorage.setItem('aml-language',lang);document.documentElement.lang=lang;},[lang]);
 const graph=useMemo(()=>data?visibleGraph(data,selected,mode,cluster,previous,hops,direction):null,[data,selected,mode,cluster,previous,hops,direction]);
 const seeds=useMemo(()=>data?data.nodes.filter(n=>n.is_seed).sort((a,b)=>a.gid.localeCompare(b.gid)):[],[data]);
 const ranked=useMemo(()=>data?[...data.nodes].sort((a,b)=>b.priority_score-a.priority_score||b.role_score-a.role_score||a.gid.localeCompare(b.gid)):[],[data]);
 const inspected=hovered||data?.nodes.find(n=>n.gid===selected);
 async function run(){
  setBusy(true);setError('');
  try{
   const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({input_dir:folder})});
   const result=await response.json();if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:t.failed);
   setData(result);setSelected(null);setHovered(null);setCluster('all');setMode('all');setQuery('');setHistory([]);setOrigin(null);
  }catch(e){setError(e instanceof TypeError?t.networkError:e.message);}finally{setBusy(false);}
 }
 function focus(id){setSelected(id);setQuery(id);setCluster('all');setMode('neighborhood');setHovered(null);setError('');setHistory([]);setOrigin(data.nodes.find(n=>n.gid===id)?.is_seed?id:null);}
 function navigate(id){if(id===selected)return;setHistory(h=>selected?[...h,selected]:h);setSelected(id);setQuery(id);setHovered(null);setMode('neighborhood');setCluster('all');}
 function back(){if(!previous)return;setSelected(previous);setQuery(previous);setHistory(h=>h.slice(0,-1));setHovered(null);}
 function search(e){e.preventDefault();if(data?.nodes.some(n=>n.gid===query.trim()))focus(query.trim());else setError(t.missing);}
 return <div className="app">
  <header><div className="brand"><span className="brand-icon">◈</span><div><b>AML GRAPH</b><small>{t.subtitle}</small></div></div><select aria-label={t.language} value={lang} onChange={e=>setLang(e.target.value)}><option value="en">English</option><option value="ru">Русский</option></select></header>
  <div className="workspace"><aside>
   <label>{t.folder}<input value={folder} onChange={e=>setFolder(e.target.value)} spellCheck="false"/></label>
   <button className="primary" onClick={run} disabled={busy}>{busy?t.running:t.run}<span>↗</span></button>
   {data&&<div className="seed-controls"><label>{t.seedPicker}<select aria-label={t.seedPicker} value={origin||''} onChange={e=>{if(e.target.value)focus(e.target.value);}}><option value="">{t.chooseSeed}</option>{seeds.map(n=><option key={n.gid} value={n.gid}>{n.gid} · ↓{n.in_degree} ↑{n.out_degree}</option>)}</select></label>
   <div className="trace-controls"><label>{t.hops}<select aria-label={t.hops} value={hops} onChange={e=>setHops(Number(e.target.value))}>{[1,2,3,4].map(h=><option key={h}>{h}</option>)}</select></label><label>{t.direction}<select aria-label={t.direction} value={direction} onChange={e=>setDirection(e.target.value)}>{['both','in','out'].map(d=><option key={d} value={d}>{t[d]}</option>)}</select></label></div></div>}
   <details className="help"><summary>{t.priorityHelp}</summary><p>{t.priorityExplanation}</p></details>
   {data&&<><details className="help"><summary>{featureText[lang].clusterHelp}</summary><p>{featureText[lang].clusterExplanation}</p><p>{featureText[lang].communities}: {data.report.n_clusters} · {t.components}: {data.report.n_components}</p></details><Resilience key={data.dataset_id} data={data} lang={lang} onNavigate={focus}/></>}
   <div className="divider"/><h2>{t.top}</h2>
   <div className="rank-list">{ranked.slice(0,20).map((n,i)=><button key={n.gid} className={'rank '+(selected===n.gid?'active':'')} onClick={()=>focus(n.gid)}><span className="rank-number">{String(i+1).padStart(2,'0')}</span><span><code>{n.gid}</code><small style={{color:colors[n.role]}}>{roles[lang][n.role]}</small></span><span>{n.priority_score.toFixed(4)}</span></button>)}</div>
   {data&&<div className="downloads"><h2>{t.exports}</h2>{['nodes_roles','clusters','top_nodes'].map(name=><a key={name} href={'/api/exports/'+name+'.csv'} download>{name}.csv <span>↓</span></a>)}</div>}
  </aside><main>
   <div className="title-row"><div><span className="eyebrow">AML / GRAPH EXPLORER</span><h1>{t.title}</h1></div>{data&&<div className="stats"><span><b>{data.report.n_nodes.toLocaleString()}</b>{t.nodes}</span><span><b>{data.report.n_edges.toLocaleString()}</b>{t.edges}</span><span><b>{data.report.n_seed}</b>{t.seeds}</span><span><b>{data.elapsed_seconds}{t.seconds}</b>{t.time}</span></div>}</div>
   {error&&<div className="error" role="alert">{error}</div>}
   <div className="toolbar"><form onSubmit={search}><input aria-label={t.search} placeholder={t.search} value={query} onChange={e=>setQuery(e.target.value)} inputMode="numeric"/><button disabled={!data}>{t.find}</button></form>
    <select aria-label={t.cluster} value={cluster} onChange={e=>{setCluster(e.target.value);setMode('all');setHovered(null);setSelected(null);setQuery('');setHistory([]);setOrigin(null);}}><option value="all">{t.all}</option>
     <optgroup label={featureText[lang].communities}>{data?.clusters.filter(c=>c.n_nodes>1).map(c=><option key={c.cluster_id} value={c.cluster_id}>{t.cluster} {c.cluster_id} · {c.n_nodes} {t.nodes.toLowerCase()}</option>)}</optgroup>
     <optgroup label={featureText[lang].singletons}>{data?.clusters.filter(c=>c.n_nodes===1).map(c=><option key={c.cluster_id} value={c.cluster_id}>{t.cluster} {c.cluster_id} · {c.top_gids}</option>)}</optgroup>
    </select>
    <select aria-label={t.color} value={color} onChange={e=>setColor(e.target.value)}><option value="role">{t.role}</option><option value="cluster">{t.cluster}</option></select>
    <button onClick={()=>{setMode('all');setCluster('all');setSelected(null);setHovered(null);setHistory([]);setOrigin(null);}}>{t.overview}</button>
   </div>
   <section className="graph-workspace" aria-label={t.title}>
    {data&&<Chat key={'chat-'+data.dataset_id} data={data} selected={selected} lang={lang} onNavigate={focus}/>}
    {graph?<Graph graph={graph} selected={selected} previous={previous} onBack={back} neighborhood={mode==='neighborhood'} onSelect={navigate} onHover={setHovered} color={color} t={t}/>:<div className="empty"><span>◈</span><h2>{t.title}</h2><p>{t.empty}</p></div>}
    {origin&&<button className="origin" onClick={()=>focus(origin)}>{t.origin}: {origin}</button>}
    {graph&&graph.edges.length===0&&<p className="no-edges">{t.noEdges}</p>}
    {graph&&<div className="graph-meta">{mode==='all'?t.overview:t.neighborhood} · {graph.nodes.length} {t.nodes.toLowerCase()} · {graph.edges.length} {t.edges.toLowerCase()}</div>}
    <div className="legend">{color==='role'?Object.entries(colors).map(([role,c])=><span key={role}><i style={{background:c}}/>{roles[lang][role]}</span>):<span>{t.cluster}</span>}</div>
    {data&&<NodeCard key={data.dataset_id} data={data} node={inspected} selected={selected} lang={lang} onNavigate={focus}/>}
   </section><footer><span>{t.hint}</span><span>{t.review}</span></footer>
   <details className="help coverage"><summary>{t.limitations}</summary><p>{t.limits}</p>{data&&<div className="coverage-counts">{[['isolatedSeeds','n_isolated_seed'],['noOutgoingSeeds','n_seed_without_outgoing'],['boundaryNodes','n_boundary'],['components','n_components'],['connectedComponents','n_connected_components']].map(([label,key])=><span key={key}>{t[label]}: <b>{data.report[key]}</b></span>)}</div>}</details>
  </main></div>
 </div>;
}
createRoot(document.getElementById('root')).render(<App/>);
