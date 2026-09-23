// Layout is visual only: it never contributes to analytical scores.
export function visibleGraph(data, selected, mode, cluster) {
 let ids = new Set(data.nodes.filter(n=>cluster==='all'||String(n.component_id)===cluster).map(n=>n.gid));
 if(mode==='neighborhood' && selected){
  const neighbors=new Set([selected]);
  data.edges.forEach(e=>{if(e.src===selected) neighbors.add(e.dst); if(e.dst===selected) neighbors.add(e.src);});
  ids=new Set([...ids].filter(id=>neighbors.has(id)));
 }
 return {nodes:data.nodes.filter(n=>ids.has(n.gid)),edges:data.edges.filter(e=>ids.has(e.src)&&ids.has(e.dst))};
}
export function layout(nodes, edges=[]) {
 // Start with a staggered depth layout, then relax it. This preserves flow
 // direction without turning every cluster into a rigid square or circle.
 const sorted=[...nodes].sort((a,b)=>a.depth-b.depth||a.component_id-b.component_id||a.gid.localeCompare(b.gid));
 const depths=[...new Set(sorted.map(n=>n.depth))].sort((a,b)=>a-b);
 const depthIndex=new Map(depths.map((depth,index)=>[depth,index]));
 const components=[...new Set(sorted.map(n=>n.component_id))].sort((a,b)=>a-b);
 const positions=new Map();
 const spacing=72;
 const depthWidth=Math.max(210,Math.min(330,spacing*Math.sqrt(sorted.length)+80));
 const componentGap=Math.max(90,Math.min(240,spacing*1.6));
 const componentCenter=new Map();
 components.forEach((component,index)=>componentCenter.set(component,(index-(components.length-1)/2)*componentGap));

 const depthGroups=new Map();
 sorted.forEach(node=>{if(!depthGroups.has(node.depth))depthGroups.set(node.depth,[]);depthGroups.get(node.depth).push(node);});
 sorted.forEach((node,index)=>{
  const sameDepth=depthGroups.get(node.depth);
  const rank=sameDepth.indexOf(node);
  const rowOffset=(rank-(sameDepth.length-1)/2)*spacing;
  // A small deterministic offset prevents identical depth/component groups
  // from starting as a perfect grid.
  const stagger=((index*0.618)%1-.5)*spacing*.45;
  positions.set(node.gid,{
   x:depthIndex.get(node.depth)*depthWidth,
   y:componentCenter.get(node.component_id)+rowOffset+stagger
  });
 });

 const nodeById=new Map(nodes.map(node=>[node.gid,node]));
 const links=edges.filter(edge=>nodeById.has(edge.src)&&nodeById.has(edge.dst));
 const iterations=sorted.length>180?45:70;
 for(let iteration=0;iteration<iterations;iteration++){
  const forces=new Map(sorted.map(node=>[node.gid,{x:0,y:0}]));
  const cooling=1-iteration/iterations;
  for(let i=0;i<sorted.length;i++) for(let j=i+1;j<sorted.length;j++){
   const a=sorted[i],b=sorted[j],pa=positions.get(a.gid),pb=positions.get(b.gid);
   const dx=pb.x-pa.x,dy=pb.y-pa.y,dist=Math.max(1,Math.hypot(dx,dy));
   const force=(dist<150?2600:700)/(dist*dist);
   const fx=dx/dist*force,fy=dy/dist*force;
   forces.get(a.gid).x-=fx;forces.get(a.gid).y-=fy;
   forces.get(b.gid).x+=fx;forces.get(b.gid).y+=fy;
  }
  links.forEach(edge=>{
   const a=positions.get(edge.src),b=positions.get(edge.dst); if(!a||!b)return;
   const dx=b.x-a.x,dy=b.y-a.y,dist=Math.max(1,Math.hypot(dx,dy));
   const force=(dist-125)*.008,fx=dx/dist*force,fy=dy/dist*force;
   forces.get(edge.src).x+=fx;forces.get(edge.src).y+=fy;
   forces.get(edge.dst).x-=fx;forces.get(edge.dst).y-=fy;
  });
  sorted.forEach(node=>{
   const p=positions.get(node.gid),f=forces.get(node.gid);
   const targetX=depthIndex.get(node.depth)*depthWidth;
   const targetY=componentCenter.get(node.component_id);
   f.x+=(targetX-p.x)*.045;
   f.y+=(targetY-p.y)*.002;
   p.x+=Math.max(-18,Math.min(18,f.x))*cooling;
   p.y+=Math.max(-18,Math.min(18,f.y))*cooling;
  });
 }
 return positions;
}
