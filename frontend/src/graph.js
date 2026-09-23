// All coordinates/forces below are presentation only. They never affect AML metrics.
export function visibleGraph(data, selected, mode, cluster, previous=null, hops=1, direction='both') {
 const allowed=new Set(data.nodes.filter(n=>cluster==='all'||String(n.cluster_id)===String(cluster)).map(n=>n.gid));
 let ids=allowed;
 if(mode==='neighborhood'&&selected){
  const adjacency=new Map([...allowed].map(id=>[id,[]]));
  for(const e of data.edges){
   if(!allowed.has(e.src)||!allowed.has(e.dst))continue;
   if(direction!=='in')adjacency.get(e.src).push(e.dst);
   if(direction!=='out')adjacency.get(e.dst).push(e.src);
  }
  ids=new Set(allowed.has(selected)?[selected]:[]);let frontier=[...ids];
  for(let i=0;i<Math.min(4,Math.max(1,hops));i++){
   const next=[];
   for(const id of frontier)for(const other of adjacency.get(id)||[])if(!ids.has(other)){ids.add(other);next.push(other);}
   frontier=next;
  }
  if(previous&&allowed.has(previous))ids.add(previous);
 }
 return {nodes:data.nodes.filter(n=>ids.has(n.gid)),edges:data.edges.filter(e=>ids.has(e.src)&&ids.has(e.dst))};
}

export function bounds(positions) {
 let minX=Infinity,maxX=-Infinity,minY=Infinity,maxY=-Infinity;
 for(const p of positions.values()){
  if(!Number.isFinite(p.x)||!Number.isFinite(p.y))continue;
  minX=Math.min(minX,p.x);maxX=Math.max(maxX,p.x);minY=Math.min(minY,p.y);maxY=Math.max(maxY,p.y);
 }
 return minX===Infinity?{minX:0,maxX:0,minY:0,maxY:0}:{minX,maxX,minY,maxY};
}

export function fitViewport(positions,width,height,detail=false) {
 const w=Math.max(1,width),h=Math.max(1,height),b=bounds(positions);
 // Keep nodes clear of legends, bottom controls, and the selected-node card.
 const left=Math.min(42,w*.08),top=Math.min(148,h*.27),bottom=Math.min(112,h*.22);
 const right=detail&&w>740?346:Math.min(42,w*.08);
 const availableW=Math.max(1,w-left-right),availableH=Math.max(1,h-top-bottom);
 const k=Math.max(.001,Math.min(1.8,availableW/Math.max(100,b.maxX-b.minX+70),availableH/Math.max(100,b.maxY-b.minY+70)));
 return {x:left+availableW/2-(b.minX+b.maxX)/2*k,y:top+availableH/2-(b.minY+b.maxY)/2*k,k};
}

function localLayout(nodes,edges,anchor) {
 if(nodes.length===1)return new Map([[nodes[0].gid,{x:0,y:0}]]);
 const adjacency=new Map(nodes.map(n=>[n.gid,new Set()]));
 for(const e of edges){if(adjacency.has(e.src)&&adjacency.has(e.dst)){adjacency.get(e.src).add(e.dst);adjacency.get(e.dst).add(e.src);}}
 const ordered=[...nodes].sort((a,b)=>adjacency.get(b.gid).size-adjacency.get(a.gid).size||a.gid.localeCompare(b.gid));
 const root=anchor&&adjacency.has(anchor)?anchor:ordered[0]?.gid;
 const distance=new Map([[root,0]]),queue=[root];
 for(let i=0;i<queue.length;i++)for(const other of [...(adjacency.get(queue[i])||[])].sort())if(!distance.has(other)){distance.set(other,distance.get(queue[i])+1);queue.push(other);}
 const rings=new Map(),positions=new Map(),unreached=Math.max(1,...distance.values())+1;
 for(const n of ordered){const level=distance.get(n.gid)??unreached;if(!rings.has(level))rings.set(level,[]);rings.get(level).push(n);}
 let radius=0;
 for(const [level,members] of [...rings].sort((a,b)=>a[0]-b[0])){
  if(level===0){positions.set(root,{x:0,y:0});continue;}
  radius=Math.max(radius+100,members.length*35/(2*Math.PI));
  members.sort((a,b)=>a.gid.localeCompare(b.gid)).forEach((n,i)=>{
   const angle=2*Math.PI*i/members.length+level*.21;
   positions.set(n.gid,{x:radius*Math.cos(angle),y:radius*Math.sin(angle)});
  });
 }
 // Spatial hashing bounds collision work; spring distances do not use money or risk.
 const links=edges.filter(e=>positions.has(e.src)&&positions.has(e.dst)).sort((a,b)=>a.src.localeCompare(b.src)||a.dst.localeCompare(b.dst));
 const ids=[...positions.keys()];
 for(let tick=0;tick<100;tick++){
  const force=new Map(ids.map(id=>[id,{x:0,y:0}])),grid=new Map(),cell=58;
  for(const id of ids){const p=positions.get(id),key=Math.floor(p.x/cell)+','+Math.floor(p.y/cell);if(!grid.has(key))grid.set(key,[]);grid.get(key).push(id);}
  for(const id of ids){
   const p=positions.get(id),f=force.get(id),gx=Math.floor(p.x/cell),gy=Math.floor(p.y/cell);
   for(let x=gx-1;x<=gx+1;x++)for(let y=gy-1;y<=gy+1;y++)for(const other of grid.get(x+','+y)||[]){
    if(other===id)continue;const q=positions.get(other);let dx=p.x-q.x,dy=p.y-q.y,d=Math.hypot(dx,dy);
    if(d<.01){dx=id<other?1:-1;dy=.5;d=Math.hypot(dx,dy);}
    if(d<cell){const push=(cell-d)*.22;f.x+=dx/d*push;f.y+=dy/d*push;}
   }
  }
  for(const e of links){const a=positions.get(e.src),b=positions.get(e.dst),dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1;
   const spring=Math.max(-2,Math.min(5,(d-105)*.025)),fx=dx/d*spring,fy=dy/d*spring;
   force.get(e.src).x+=fx;force.get(e.src).y+=fy;force.get(e.dst).x-=fx;force.get(e.dst).y-=fy;
  }
  for(const id of ids){if(id===root)continue;const p=positions.get(id),f=force.get(id),cool=1-tick/140;
   p.x+=Math.max(-9,Math.min(9,f.x))*cool;p.y+=Math.max(-9,Math.min(9,f.y))*cool;
  }
 }
 return positions;
}

export function layout(nodes,anchor=null,edges=[]) {
 if(!nodes.length)return new Map();
 if(anchor)return localLayout(nodes,edges,anchor);
 const groups=new Map(),owner=new Map();
 for(const n of nodes){const key=String(n.cluster_id??0);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(n);owner.set(n.gid,key);}
 const links=new Map([...groups.keys()].map(key=>[key,[]]));
 for(const e of edges)if(owner.has(e.src)&&owner.get(e.src)===owner.get(e.dst))links.get(owner.get(e.src)).push(e);
 const regions=[...groups].map(([id,members])=>{
  const points=localLayout(members,links.get(id),null),b=bounds(points);
  return {id,points,b,w:Math.max(130,b.maxX-b.minX+130),h:Math.max(130,b.maxY-b.minY+130)};
 }).sort((a,b)=>b.h-a.h||Number(a.id)-Number(b.id));
 if(regions.length===1)return regions[0].points;
 const width=Math.max(...regions.map(r=>r.w),Math.sqrt(regions.reduce((s,r)=>s+r.w*r.h,0))*1.5);
 const result=new Map();let x=0,y=0,row=0;
 for(const r of regions){
  if(x>0&&x+r.w>width){x=0;y+=row;row=0;}
  for(const [id,p] of r.points)result.set(id,{x:p.x-r.b.minX+x+65,y:p.y-r.b.minY+y+65});
  x+=r.w;row=Math.max(row,r.h);
 }
 return result;
}

export const edgeColors={incoming:'#9abfe2',outgoing:'#e0b59b',other:'#8598ae'};
export function edgeColor(edge,selected){return edge.dst===selected?edgeColors.incoming:edge.src===selected?edgeColors.outgoing:edgeColors.other;}
export function curve(a,b,src,dst){
 const dx=b.x-a.x,dy=b.y-a.y,length=Math.hypot(dx,dy)||1;
 let hash=0;for(const c of src+'>'+dst)hash=(hash*31+c.charCodeAt(0))>>>0;
 const bend=Math.min(65,Math.max(12,length*.13))+(hash%11);
 return {x:(a.x+b.x)/2-dy/length*bend,y:(a.y+b.y)/2+dx/length*bend};
}
