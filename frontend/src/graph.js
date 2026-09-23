// Layout is visual only: it never contributes to analytical scores.
export function visibleGraph(data, selected, mode, cluster, previous=null, hops=1, direction='both') {
 let ids = new Set(data.nodes.filter(n=>cluster==='all'||String(n.cluster_id)===cluster).map(n=>n.gid));
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
export function layout(nodes, anchor=null, edges=[]) {
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
 return denseLayout(nodes, edges);
}
function denseLayout(nodes, edges=[]) {
 // Pack community regions so a 2,000-node component cannot become one thin column.
 // Sunflower positions and all spacing below are rendering-only, never metrics.
 const groups=new Map();
 [...nodes].sort((a,b)=>a.cluster_id-b.cluster_id||a.depth-b.depth||a.gid.localeCompare(b.gid)).forEach(node=>{
  if(!groups.has(node.cluster_id))groups.set(node.cluster_id,[]);
  groups.get(node.cluster_id).push(node);
 });
 const regions=[...groups.entries()].map(([id,members])=>({id,members,radius:Math.max(45,Math.sqrt(members.length)*28+45)}));
 regions.sort((a,b)=>b.radius-a.radius||a.id-b.id);
 const shelfWidth=Math.max(400,Math.sqrt(regions.reduce((sum,r)=>sum+(2*r.radius+60)**2,0))*1.25);
 const positions=new Map(),targets=new Map();
 let x=0,y=0,rowHeight=0;
 for(const region of regions){
  const diameter=region.radius*2+60;
  if(x+diameter>shelfWidth&&x>0){x=0;y+=rowHeight;rowHeight=0;}
  const cx=x+region.radius,cy=y+region.radius;
  region.members.forEach((node,index)=>{
   const angle=index*Math.PI*(3-Math.sqrt(5)),radius=Math.sqrt(index)*28;
   const p={x:cx+Math.cos(angle)*radius,y:cy+Math.sin(angle)*radius};
   positions.set(node.gid,p);targets.set(node.gid,{...p});
  });
  x+=diameter;rowHeight=Math.max(rowHeight,diameter);
 }
 const ordered=[...nodes].sort((a,b)=>a.gid.localeCompare(b.gid));
 const links=edges.filter(edge=>positions.has(edge.src)&&positions.has(edge.dst));
 // Mild spring relaxation keeps groups legible while bringing direct links closer.
 for(let iteration=0;iteration<25;iteration++){
  const forces=new Map(ordered.map(n=>[n.gid,{x:0,y:0}]));
  for(const edge of links){
   const a=positions.get(edge.src),b=positions.get(edge.dst);
   const dx=b.x-a.x,dy=b.y-a.y,length=Math.hypot(dx,dy)||1;
   const force=Math.min(4,(length-80)*.008);
   const fx=dx/length*force,fy=dy/length*force;
   forces.get(edge.src).x+=fx;forces.get(edge.src).y+=fy;
   forces.get(edge.dst).x-=fx;forces.get(edge.dst).y-=fy;
  }
  for(const node of ordered){
   const p=positions.get(node.gid),f=forces.get(node.gid),target=targets.get(node.gid);
   p.x+=Math.max(-4,Math.min(4,f.x+(target.x-p.x)*.25));
   p.y+=Math.max(-4,Math.min(4,f.y+(target.y-p.y)*.25));
  }
 }
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
