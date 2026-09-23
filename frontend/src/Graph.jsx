import React,{useRef,useEffect,useState} from 'react';
import {CanvasScene} from './CanvasScene.js';
import {edgeColors,layout} from './graph.js';

export default function Graph(props){
 const {graph,selected,previous,onBack,color,t,neighborhood}=props;
 const canvas=useRef(null),marker=useRef(null),scene=useRef(null),sequence=useRef(0),latest=useRef(props);
 const [busy,setBusy]=useState(true);
 latest.current=props;
 useEffect(()=>{
  const renderer=new CanvasScene(canvas.current,marker.current,{
   select:id=>latest.current.onSelect(id),hover:n=>latest.current.onHover(n)
  });
  scene.current=renderer;
  return()=>{renderer.destroy();scene.current=null;};
 },[]);
 useEffect(()=>{scene.current?.update({selected,previous,color,neighborhood});},[selected,previous,color,neighborhood]);
 const anchor=neighborhood?selected:null;
 useEffect(()=>{
  const id=++sequence.current;
  setBusy(true);scene.current.setPending();
  const install=positions=>{
   if(id!==sequence.current)return;
   scene.current.setGraph(graph,positions);setBusy(false);
  };
  // A worker keeps layout off the UI thread. Terminate superseded jobs so a
  // rapid filter change can never install an old cluster's coordinates.
  let job;
  const fallback=()=>install(layout(graph.nodes,anchor,graph.edges));
  try{
   job=new Worker(new URL('./layout.worker.js',import.meta.url),{type:'module'});
   job.onmessage=({data})=>{if(data.id!==sequence.current)return;if(data.error)fallback();else install(new Map(data.positions));};
   job.onerror=fallback;
   job.postMessage({id,nodes:graph.nodes,edges:graph.edges,anchor});
  }catch{fallback();}
  return()=>{if(sequence.current===id)sequence.current++;job?.terminate();};
 },[graph,anchor]);
 return <>
  <canvas ref={canvas} tabIndex={0} aria-label={t.title} aria-busy={busy}/>
  <button ref={marker} hidden className="previous-marker" title={t.back+': '+previous} aria-label={t.back+': '+previous} onClick={onBack}>↶</button>
  {busy&&<div className="layout-progress" role="status">{t.running}</div>}
  <div className="edge-legend" title={t.directionHelp}><span style={{color:edgeColors.incoming}}>→ {t.in}</span><span style={{color:edgeColors.outgoing}}>→ {t.out}</span></div>
  <div className="map-controls"><button onClick={()=>scene.current.zoom(1.4)} aria-label={t.zoomIn}>+</button><button onClick={()=>scene.current.zoom(1/1.4)} aria-label={t.zoomOut}>−</button><button onClick={()=>scene.current.fit()}>{t.reset}</button>{previous&&<button onClick={onBack}>↶ {t.back}</button>}</div>
 </>;
}
