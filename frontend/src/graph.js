// Layout is visual only: it never contributes to analytical scores.
export function visibleGraph(data, selected, mode, cluster, previous=null, hops=1, direction='both') {
 let ids = new Set(data.nodes.filter(n=>cluster==='all'||String(n.component_id)===cluster).map(n=>n.gid));
 if(mode==='neighborhood' && selected){
  const neighbors=new Set([selected]);
  let frontier=new Set([selected]);
  for(let i=0;i<hops;i++){
   const next=new Set();
   data.edges.forEach(e=>{if(direction!=='in'&&frontier.has(e.src)) next.add(e.dst); if(direction!=='out'&&frontier.has(e.dst))next.add(e.src);});
   frontier=new Set([...next].filter(id=>!neighbors.has(id)));frontier.forEach(id=>neighbors.add(id));
  }
  if(previous)neighbors.add(previous);
  ids=new Set([...ids].filter(id=>neighbors.has(id)));
 }
 return {nodes:data.nodes.filter(n=>ids.has(n.gid)),edges:data.edges.filter(e=>ids.has(e.src)&&ids.has(e.dst))};
}
export function layout(nodes, anchor=null) {
 if(anchor && nodes.some(n=>n.gid===anchor)){
  const positions=new Map([[anchor,{x:0,y:0}]]);
  const others=nodes.filter(n=>n.gid!==anchor).sort((a,b)=>a.gid.localeCompare(b.gid));
  let start=0,ring=1;
  while(start<others.length){
   const count=Math.min(others.length-start,ring*16),radius=160*ring;
   for(let i=0;i<count;i++){
    const angle=2*Math.PI*(i/count+ring*.039);
    positions.set(others[start+i].gid,{x:radius*Math.cos(angle),y:radius*Math.sin(angle)});
   }
   start+=count;ring++;
  }
  return positions;
 }
 const groups=new Map();
 nodes.forEach(n=>{const key=n.depth; if(!groups.has(key))groups.set(key,[]);groups.get(key).push(n);});
 const depths=[...groups.keys()].sort((a,b)=>a-b);
 const positions=new Map();
 let offset=0;
 depths.forEach(depth=>{
  const group=groups.get(depth).slice().sort((a,b)=>a.component_id-b.component_id||a.gid.localeCompare(b.gid));
  const cols=Math.max(1,Math.ceil(Math.sqrt(group.length/3)));
  const rows=Math.ceil(group.length/cols);
  group.forEach((n,j)=>positions.set(n.gid,{x:offset+(j%cols)*35+(j%3)*3,y:(Math.floor(j/cols)-rows/2)*35+(j%cols)*6}));
  offset+=Math.max(240,cols*35+160);
 });
 return positions;
}

export const edgeColors={incoming:'#96bce2',outgoing:'#d8b49b',other:'#52647b'};
export function edgeColor(edge, selected){return edge.dst===selected?edgeColors.incoming:edge.src===selected?edgeColors.outgoing:edgeColors.other;}
export function curve(a,b,src,dst){
 // A stable bend distinguishes collinear routes; reverse edges bend to the other side.
 const dx=b.x-a.x,dy=b.y-a.y,length=Math.hypot(dx,dy)||1;
 let hash=0;for(const c of src+'>'+dst)hash=(hash*31+c.charCodeAt(0))>>>0;
 const bend=Math.min(70,Math.max(20,length*.14))+(hash%17);
 return {x:(a.x+b.x)/2-dy/length*bend,y:(a.y+b.y)/2+dx/length*bend};
}
