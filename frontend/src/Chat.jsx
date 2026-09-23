import React,{useState,useEffect,useRef} from 'react';
import {featureText} from './features-i18n';

export default function Chat({data,selected,lang,onNavigate}){
 const t=featureText[lang],end=useRef(null);
 const [open,setOpen]=useState(false),[expanded,setExpanded]=useState(false),[messages,setMessages]=useState([]),[text,setText]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[status,setStatus]=useState(null),[usage,setUsage]=useState(null);
 const [session]=useState(()=>{const key='aml-chat-'+data.dataset_id;let id=localStorage.getItem(key);if(!id){id=crypto.randomUUID();localStorage.setItem(key,id);}return id;});
 const [checking,setChecking]=useState(false),[connected,setConnected]=useState('');
 const errorText=detail=>typeof detail==='string'?detail:t[detail?.code]||detail?.message||t.error;
 useEffect(()=>{let live=true;
  fetch(`/api/chat/history/${session}?dataset_id=${data.dataset_id}`).then(async r=>{const j=await r.json();if(!r.ok)throw new Error(j.detail);return j;}).then(j=>{if(live)setMessages(j.messages);}).catch(e=>{if(live)setError(e.message);});
  return()=>{live=false;};
 },[session,data.dataset_id]);
 useEffect(()=>{if(!open)return;let live=true;
  const refresh=()=>fetch('/api/chat/status').then(async r=>{if(!r.ok)throw new Error(t.error);return r.json();}).then(s=>{if(live)setStatus(s);}).catch(()=>{if(live)setError(t.error);});
  refresh();const timer=setInterval(refresh,10000);
  return()=>{live=false;clearInterval(timer);};
 },[open]);
 useEffect(()=>{end.current?.scrollIntoView({block:'nearest'});},[messages,open,busy]);
 async function send(e){e.preventDefault();if(!text.trim()||busy)return;setBusy(true);setError('');
  const question=text.trim();
  try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:session,dataset_id:data.dataset_id,message:question,selected_gid:selected,language:lang})});const j=await r.json();if(!r.ok)throw new Error(errorText(j.detail));
   setMessages(m=>[...m,{role:'user',content:question},{role:'assistant',content:j.answer,gids:j.gids}]);setUsage(j);setText('');
  }catch(e){setError(e.message);}finally{setBusy(false);}
 }
 async function check(){
  setChecking(true);setConnected('');setError('');
  try{
   const statusResponse=await fetch('/api/chat/status');if(statusResponse.ok)setStatus(await statusResponse.json());
   const r=await fetch('/api/chat/check',{method:'POST'}),j=await r.json();
   if(!r.ok)throw new Error(errorText(j.detail));setConnected(j.model);
  }catch(e){setError(e instanceof TypeError?t.connection:e.message);}finally{setChecking(false);}
 }
 async function clear(){try{const r=await fetch('/api/chat/history/'+session,{method:'DELETE'});if(!r.ok)throw new Error(t.resetError);setMessages([]);setUsage(null);setError('');}catch(e){setError(e.message);}}
 const render=m=>m.content.split(/(\[gid:\d+\])/g).map((part,i)=>{const id=part.match(/^\[gid:(\d+)\]$/)?.[1];return id&&m.gids?.includes(id)?<button className="citation" key={i} onClick={()=>onNavigate(id)}>{id}</button>:<React.Fragment key={i}>{part}</React.Fragment>;});
 return <section className={'chat '+(open?'open ':'')+(expanded?'expanded':'')} aria-label={t.assistant}>
  <div className="chat-heading"><button onClick={()=>{setOpen(!open);if(open)setExpanded(false);}}>✧ {t.assistant} {open?'−':'+'}</button>{open&&<><button onClick={()=>setExpanded(!expanded)}>{expanded?t.collapse:t.expand}</button><button disabled={busy} onClick={clear}>{t.clear}</button></>}</div>
  {open&&<><p className="chat-note">{t.privacy} {t.memory}</p>{status&&!status.configured&&<p className="warning">{t.keyMissing}</p>}
  <div className="chat-connection"><span>{connected?t.connected: t.model}: {connected||status?.model||'…'}</span><button disabled={checking||busy} onClick={check} title={t.checkNote}>{checking?t.checking:t.checkConnection}</button></div>
  <div className="chat-messages" aria-live="polite">{messages.map((m,i)=><div className={'message '+m.role} key={i}>{render(m)}</div>)}{busy&&<p>{t.thinking}</p>}<div ref={end}/></div>
  {error&&<p className="chat-error" role="alert">{error}</p>}{usage&&<small>{t.usage}: {usage.usage.input_tokens}/{usage.usage.output_tokens} · {t.tools}: {usage.queries.length}</small>}
  <form onSubmit={send}><textarea aria-label={t.placeholder} placeholder={t.placeholder} maxLength={2000} value={text} onChange={e=>setText(e.target.value)}/><button disabled={busy||checking||!status?.configured||!text.trim()}>{t.send}</button></form></>}
 </section>;
}
