import {bounds,curve,edgeColor,fitViewport} from './graph.js';
import {colors} from './i18n.js';

// One imperative scene owns drawing, hit-testing, camera and animation. React
// never rerenders 2,248 nodes or resizes the backing canvas on animation frames.
export class CanvasScene {
 constructor(canvas,marker,callbacks){
  this.canvas=canvas;this.marker=marker;this.callbacks=callbacks;
  this.graph={nodes:[],edges:[]};this.positions=new Map();this.from=new Map();
  this.camera={x:0,y:0,k:1};this.size={w:1,h:1};this.hover=null;this.pending=true;
  this.reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  this.listeners=[];this.frame=0;this.started=0;
  const listen=(name,handler,options)=>{canvas.addEventListener(name,handler,options);this.listeners.push([name,handler,options]);};
  listen('wheel',e=>{e.preventDefault();this.zoom(Math.exp(-e.deltaY*.0015),this.point(e));},{passive:false});
  listen('pointerdown',e=>{if(e.button!==0||this.pending)return;this.drag={...this.point(e),start:this.point(e),moved:false};this.cameraMotion=null;canvas.setPointerCapture(e.pointerId);});
  listen('pointermove',e=>this.move(e));
  listen('pointerup',e=>{
   if(this.drag&&!this.drag.moved){const hit=this.hit(this.point(e));if(hit)this.callbacks.select(hit.gid);}
   this.drag=null;if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);
  });
  listen('pointercancel',()=>{this.drag=null;});
  listen('lostpointercapture',()=>{this.drag=null;});
  listen('pointerleave',()=>{if(!this.drag)this.setHover(null);});
  listen('keydown',e=>{
   if(e.key==='+'||e.key==='='){e.preventDefault();this.zoom(1.4);}
   if(e.key==='-'){e.preventDefault();this.zoom(1/1.4);}
   if(e.key==='0'){e.preventDefault();this.fit();}
   const d={ArrowLeft:[40,0],ArrowRight:[-40,0],ArrowUp:[0,40],ArrowDown:[0,-40]}[e.key];
   if(d){e.preventDefault();this.cameraMotion=null;this.camera.x+=d[0];this.camera.y+=d[1];this.schedule();}
  });
  this.observer=new ResizeObserver(entries=>{
   const rect=entries[0].contentRect;if(rect.width<1||rect.height<1)return;
   this.size={w:rect.width,h:rect.height};
   this.dpr=Math.min(2,window.devicePixelRatio||1);
   canvas.width=Math.round(rect.width*this.dpr);canvas.height=Math.round(rect.height*this.dpr);
   this.fit();
  });
  this.observer.observe(canvas);
 }
 destroy(){cancelAnimationFrame(this.frame);this.observer.disconnect();for(const args of this.listeners)this.canvas.removeEventListener(...args);}
 point(e){const r=this.canvas.getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top};}
 screen(id){const p=this.current?.get(id)||this.positions.get(id);return p?{x:p.x*this.camera.k+this.camera.x,y:p.y*this.camera.k+this.camera.y}:null;}
 radius(n){return Math.min(7,Math.max(2.2,3+this.camera.k*2))+(n.gid===this.selected||n.gid===this.hover?2:0);}
 hit(p){
  if(this.pending)return null;let found=null,closest=Infinity;
  for(const n of this.graph.nodes){const q=this.screen(n.gid);if(!q)continue;const d=Math.hypot(p.x-q.x,p.y-q.y);if(d<Math.max(7,this.radius(n)+3)&&d<closest){found=n;closest=d;}}
  return found;
 }
 setHover(node){if(this.hover===(node?.gid||null))return;this.hover=node?.gid||null;this.canvas.style.cursor=node?'pointer':'grab';this.callbacks.hover(node);this.schedule();}
 move(e){
  const p=this.point(e);
  if(this.drag){const d=this.drag;this.cameraMotion=null;this.camera.x+=p.x-d.x;this.camera.y+=p.y-d.y;d.moved ||= Math.hypot(p.x-d.start.x,p.y-d.start.y)>4;d.x=p.x;d.y=p.y;this.schedule();}
  else this.setHover(this.hit(p));
 }
 setPending(){this.pending=true;this.drag=null;this.setHover(null);this.canvas.dataset.layoutState='loading';this.marker.hidden=true;}
 setGraph(graph,positions){
  this.from=new Map(this.current||this.positions);this.positions=positions;this.graph=graph;
  this.nodesById=new Map(graph.nodes.map(n=>[n.gid,n]));
  this.started=performance.now();this.pending=false;this.current=new Map(positions);
  const groups=new Map();for(const n of graph.nodes){if(!groups.has(n.cluster_id))groups.set(n.cluster_id,new Map());groups.get(n.cluster_id).set(n.gid,positions.get(n.gid));}
  this.regions=[...groups].map(([id,p])=>({id,count:p.size,...bounds(p)}));
  this.fit();
 }
 update({selected,previous,color,neighborhood}){this.selected=selected;this.previous=previous;this.color=color;this.neighborhood=neighborhood;this.schedule();}
 animateCamera(target){this.cameraMotion={from:{...this.camera},to:target,start:performance.now()};this.schedule();}
 fit(){this.animateCamera(fitViewport(this.positions,this.size.w,this.size.h,Boolean(this.selected)));}
 zoom(factor,p={x:this.size.w/2,y:this.size.h/2}){
  const v=this.camera,k=Math.max(.001,Math.min(10,v.k*factor)),ratio=k/v.k;
  this.animateCamera({x:p.x-(p.x-v.x)*ratio,y:p.y-(p.y-v.y)*ratio,k});
 }
 schedule(){if(!this.frame)this.frame=requestAnimationFrame(now=>{this.frame=0;this.draw(now);});}
 draw(now){
  let moving=false;
  if(this.cameraMotion){const m=this.cameraMotion,p=this.reduced?1:Math.min(1,(now-m.start)/320),e=1-(1-p)**3;
   for(const key of ['x','y','k'])this.camera[key]=m.from[key]+(m.to[key]-m.from[key])*e;
   if(p===1)this.cameraMotion=null;else moving=true;
  }
  const progress=this.reduced?1:Math.min(1,(now-this.started)/360),ease=1-(1-progress)**3;
  this.current=new Map();for(const [id,end] of this.positions){const begin=this.from.get(id)||end;this.current.set(id,{x:begin.x+(end.x-begin.x)*ease,y:begin.y+(end.y-begin.y)*ease});}
  moving ||= progress<1;
  const ctx=this.canvas.getContext('2d'),{w,h}=this.size;
  ctx.setTransform(this.dpr||1,0,0,this.dpr||1,0,0);ctx.clearRect(0,0,w,h);
  if(!this.neighborhood&&this.regions?.length>1){
   for(const r of this.regions){
    const x=r.minX*this.camera.k+this.camera.x-13,y=r.minY*this.camera.k+this.camera.y-18;
    const rw=Math.max(26,(r.maxX-r.minX)*this.camera.k+26),rh=Math.max(36,(r.maxY-r.minY)*this.camera.k+36);
    ctx.fillStyle='rgba(182,206,227,.025)';ctx.strokeStyle='rgba(182,206,227,.13)';ctx.lineWidth=1;
    ctx.beginPath();ctx.roundRect(x,y,rw,rh,10);ctx.fill();ctx.stroke();
    if(rw>75){ctx.fillStyle='#9eafc1';ctx.font='10px Segoe UI';ctx.textAlign='left';ctx.fillText('#'+r.id+' · '+r.count,x+5,y-5);}
   }
  }
  const focus=this.selected||this.hover;
  // Draw background links first, then highlighted directional routes.
  for(const active of [false,true])for(const e of this.graph.edges){
   if((e.src===focus||e.dst===focus)!==active)continue;
   const a=this.screen(e.src),b=this.screen(e.dst);if(!a||!b)continue;
   if((a.x< -80&&b.x< -80)||(a.x>w+80&&b.x>w+80)||(a.y< -80&&b.y< -80)||(a.y>h+80&&b.y>h+80))continue;
   const distance=Math.hypot(b.x-a.x,b.y-a.y);if(distance<7)continue;
   const control=curve(a,b,e.src,e.dst),startAngle=Math.atan2(control.y-a.y,control.x-a.x),endAngle=Math.atan2(b.y-control.y,b.x-control.x);
   const sr=this.radius(this.nodesById.get(e.src))+1,er=this.radius(this.nodesById.get(e.dst))+3;
   const start={x:a.x+sr*Math.cos(startAngle),y:a.y+sr*Math.sin(startAngle)},end={x:b.x-er*Math.cos(endAngle),y:b.y-er*Math.sin(endAngle)};
   ctx.strokeStyle=edgeColor(e,focus);ctx.fillStyle=ctx.strokeStyle;ctx.lineWidth=active?1.7:.7;ctx.globalAlpha=active?.95:focus?.12:.28;
   ctx.beginPath();ctx.moveTo(start.x,start.y);ctx.quadraticCurveTo(control.x,control.y,end.x,end.y);ctx.stroke();
   const arrow=active?6:3.5;
   ctx.beginPath();ctx.moveTo(end.x,end.y);ctx.lineTo(end.x-arrow*Math.cos(endAngle-.5),end.y-arrow*Math.sin(endAngle-.5));ctx.lineTo(end.x-arrow*Math.cos(endAngle+.5),end.y-arrow*Math.sin(endAngle+.5));ctx.closePath();ctx.fill();
  }
  ctx.globalAlpha=1;let drawn=0;
  for(const n of this.graph.nodes){
   const p=this.screen(n.gid);if(!p||p.x< -25||p.y< -25||p.x>w+25||p.y>h+25)continue;drawn++;
   const active=n.gid===this.selected||n.gid===this.hover,r=this.radius(n);
   if(active){ctx.fillStyle='#c9e6e41c';ctx.beginPath();ctx.arc(p.x,p.y,r+7,0,2*Math.PI);ctx.fill();}
   ctx.fillStyle=this.color==='cluster'?'hsl('+(n.cluster_id*137.5%360)+' 42% 72%)':colors[n.role]||'#afc4d7';
   ctx.beginPath();ctx.arc(p.x,p.y,r,0,2*Math.PI);ctx.fill();
   if(active||n.is_seed||n.gid===this.previous){ctx.lineWidth=active?2:1;ctx.strokeStyle=active?'#eff7fa':'#cfdae7';ctx.stroke();}
   if(active||this.graph.nodes.length<=8){ctx.fillStyle='#e3ebf7';ctx.font='11px monospace';ctx.textAlign='center';ctx.fillText(n.gid,p.x,p.y-r-10);}
  }
  const previous=this.screen(this.previous);
  this.marker.hidden=this.pending||!previous||previous.x<12||previous.x>w-40||previous.y<20||previous.y>h-20;
  // Place the back badge beside the node, not on top of its exact-gid label.
  if(previous){this.marker.style.left=(previous.x+12)+'px';this.marker.style.top=(previous.y-10)+'px';}
  this.canvas.dataset.renderedNodes=String(drawn);
  if(!this.pending)this.canvas.dataset.layoutState=moving?'animating':'ready';
  if(moving)this.schedule();
 }
}
