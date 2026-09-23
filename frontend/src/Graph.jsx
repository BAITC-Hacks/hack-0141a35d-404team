import React, {useRef,useEffect,useState,useMemo} from 'react';
import {layout,curve,edgeColor,edgeColors} from './graph.js';
import {colors} from './i18n';

export default function Graph({graph,selected,previous,onBack,onSelect,onHover,color,t,neighborhood}) {
 const canvas=useRef(null), view=useRef({x:0,y:0,k:1}), drag=useRef(null), hit=useRef(null);
 const [size,setSize]=useState({w:800,h:600});
 const [version,setVersion]=useState(0);
 const positions=useMemo(()=>layout(graph.nodes,neighborhood?selected:null),[graph.nodes,neighborhood,selected]);
 const rendered=useRef(new Map()),cameraFrame=useRef(null);
 const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
 const update=()=>setVersion(v=>v+1);
 const animateView=target=>{
  cancelAnimationFrame(cameraFrame.current);
  const from={...view.current},start=performance.now();
  const tick=now=>{const p=reduced?1:Math.min(1,(now-start)/360),ease=1-Math.pow(1-p,3);
   view.current={x:from.x+(target.x-from.x)*ease,y:from.y+(target.y-from.y)*ease,k:from.k+(target.k-from.k)*ease};update();
   if(p<1)cameraFrame.current=requestAnimationFrame(tick);
  };cameraFrame.current=requestAnimationFrame(tick);
 };
 const fit=()=>{
  const ps=[...positions.values()]; if(!ps.length)return;
  const xs=ps.map(p=>p.x),ys=ps.map(p=>p.y);
  const minX=Math.min(...xs)-40,maxX=Math.max(...xs)+40,minY=Math.min(...ys)-40,maxY=Math.max(...ys)+40;
  const k=Math.min(2.5,(size.w-70)/(maxX-minX),(size.h-100)/(maxY-minY));
  animateView({x:size.w/2-(minX+maxX)/2*k,y:size.h/2-(minY+maxY)/2*k,k});
 };
 useEffect(()=>{
  const observer=new ResizeObserver(([entry])=>setSize({w:entry.contentRect.width,h:entry.contentRect.height}));
  observer.observe(canvas.current.parentElement);return()=>observer.disconnect();
 },[]);
 useEffect(()=>{fit();onHover(null);},[positions,size]);
 useEffect(()=>{
  const from=new Map(rendered.current),start=performance.now();let frame;
  const tick=now=>{const p=reduced?1:Math.min(1,(now-start)/420),ease=1-Math.pow(1-p,3);
   const next=new Map();positions.forEach((end,id)=>{const begin=from.get(id)||end;next.set(id,{x:begin.x+(end.x-begin.x)*ease,y:begin.y+(end.y-begin.y)*ease});});
   rendered.current=next;update();if(p<1)frame=requestAnimationFrame(tick);
  };frame=requestAnimationFrame(tick);return()=>cancelAnimationFrame(frame);
 },[positions]);
 useEffect(()=>()=>cancelAnimationFrame(cameraFrame.current),[]);
 useEffect(()=>{
  const c=canvas.current,dpr=window.devicePixelRatio||1;
  c.width=size.w*dpr;c.height=size.h*dpr;
  const ctx=c.getContext('2d');ctx.scale(dpr,dpr);ctx.clearRect(0,0,size.w,size.h);
  const {x,y,k}=view.current;const point=id=>{const p=rendered.current.get(id)||positions.get(id);return{x:p.x*k+x,y:p.y*k+y};};
  graph.edges.forEach(e=>{
   const a=point(e.src),b=point(e.dst),control=curve(a,b,e.src,e.dst),angle=Math.atan2(b.y-control.y,b.x-control.x),r=Math.max(4,7*k)+6;
   const end={x:b.x-r*Math.cos(angle),y:b.y-r*Math.sin(angle)};
   const active=e.src===selected||e.dst===selected;
   ctx.strokeStyle=edgeColor(e,selected);ctx.fillStyle=ctx.strokeStyle;ctx.lineWidth=active?1.8:0.65;ctx.globalAlpha=active?.95:.26;
   ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.quadraticCurveTo(control.x,control.y,end.x,end.y);ctx.stroke();
   const arrow=active?6:4;
   ctx.beginPath();ctx.moveTo(end.x,end.y);ctx.lineTo(end.x-arrow*Math.cos(angle-.5),end.y-arrow*Math.sin(angle-.5));ctx.lineTo(end.x-arrow*Math.cos(angle+.5),end.y-arrow*Math.sin(angle+.5));ctx.closePath();ctx.fill();
  });
  ctx.globalAlpha=1;
  graph.nodes.forEach(n=>{
   const p=point(n.gid);const active=n.gid===selected||n.gid===hit.current;
   const r=Math.max(4,7*k)+(active?3:0);
   ctx.fillStyle=color==='cluster'?`hsl(${n.component_id*137.5%360} 65% 66%)`:colors[n.role];
   ctx.beginPath();ctx.arc(p.x,p.y,r,0,Math.PI*2);ctx.fill();
   if(active||n.is_seed||n.gid===previous){ctx.strokeStyle=active?'#edf2f7':'#c2cddc';ctx.lineWidth=active?2:1;ctx.stroke();}
   if(active){ctx.fillStyle='#e3ebf7';ctx.font='11px monospace';ctx.textAlign='center';ctx.fillText(n.gid,p.x,p.y-r-8);}
  });
 },[graph,positions,size,version,selected,color,previous]);
 const at=e=>{const r=canvas.current.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top};};
 const zoom=(factor,p={x:size.w/2,y:size.h/2})=>{
  const v=view.current,k=Math.min(12,Math.max(.04,v.k*factor)),ratio=k/v.k;
  animateView({x:p.x-(p.x-v.x)*ratio,y:p.y-(p.y-v.y)*ratio,k});
 };
 useEffect(()=>{
  const el=canvas.current;const wheel=e=>{e.preventDefault();zoom(Math.exp(-e.deltaY*.001),at(e));};
  el.addEventListener('wheel',wheel,{passive:false});return()=>el.removeEventListener('wheel',wheel);
 },[size]);
 const move=e=>{
  const p=at(e);
  if(drag.current){cancelAnimationFrame(cameraFrame.current);const d=drag.current;view.current.x+=p.x-d.x;view.current.y+=p.y-d.y;d.moved ||= Math.abs(p.x-d.x)+Math.abs(p.y-d.y)>2;d.x=p.x;d.y=p.y;update();return;}
  let closest=null,distance=Infinity;const v=view.current;
  graph.nodes.forEach(n=>{const pos=rendered.current.get(n.gid)||positions.get(n.gid),d=Math.hypot(p.x-pos.x*v.k-v.x,p.y-pos.y*v.k-v.y);if(d<Math.max(10,7*v.k)&&d<distance){closest=n;distance=d;}});
  if(hit.current!==closest?.gid){hit.current=closest?.gid||null;onHover(closest);update();}
 };
 const prevPosition=positions.has(previous)?(rendered.current.get(previous)||positions.get(previous)):null;
 return <><canvas ref={canvas} aria-label={t.title} onPointerMove={move}
  onPointerDown={e=>{if(e.button!==0)return;move(e);canvas.current.setPointerCapture(e.pointerId);drag.current={...at(e),moved:false};}}
  onPointerUp={e=>{if(drag.current&&!drag.current.moved&&hit.current)onSelect(hit.current);drag.current=null;canvas.current.releasePointerCapture(e.pointerId);}}
  onPointerCancel={()=>{drag.current=null;}} onPointerLeave={()=>{if(!drag.current){hit.current=null;onHover(null);update();}}}/>
  {prevPosition&&<button className="previous-marker" title={`${t.back}: ${previous}`} aria-label={`${t.back}: ${previous}`} onClick={onBack} style={{left:prevPosition.x*view.current.k+view.current.x-24,top:prevPosition.y*view.current.k+view.current.y-28}}>↶</button>}
  <div className="edge-legend" title={t.directionHelp}><span style={{color:edgeColors.incoming}}>→ {t.in}</span><span style={{color:edgeColors.outgoing}}>→ {t.out}</span></div>
  <div className="map-controls"><button onClick={()=>zoom(1.4)} aria-label={t.zoomIn}>+</button><button onClick={()=>zoom(1/1.4)} aria-label={t.zoomOut}>−</button><button onClick={fit}>{t.reset}</button>{previous&&<button onClick={onBack}>↶ {t.back}</button>}</div></>;
}
