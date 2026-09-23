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
export function layout(nodes) {
 const groups=new Map();
 nodes.forEach(n=>{const key=n.depth; if(!groups.has(key))groups.set(key,[]);groups.get(key).push(n);});
 const depths=[...groups.keys()].sort((a,b)=>a-b);
 const positions=new Map();
 let offset=0;
 depths.forEach(depth=>{
  const group=groups.get(depth).slice().sort((a,b)=>a.component_id-b.component_id||a.gid.localeCompare(b.gid));
  const cols=Math.max(1,Math.ceil(Math.sqrt(group.length/3)));
  const rows=Math.ceil(group.length/cols);
  group.forEach((n,j)=>positions.set(n.gid,{x:offset+(j%cols)*35,y:(Math.floor(j/cols)-rows/2)*35}));
  offset+=Math.max(240,cols*35+160);
 });
 return positions;
}
