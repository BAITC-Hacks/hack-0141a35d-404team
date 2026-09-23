import test from 'node:test';
import assert from 'node:assert/strict';
import {visibleGraph,layout,curve,edgeColor,edgeColors,fitViewport} from '../src/graph.js';
import {dictionaries,roles,evidence} from '../src/i18n.js';
import {featureText} from '../src/features-i18n.js';

const a='100000000011452101',b='100000000011452102',c='100000000011452103';
const data={nodes:[{gid:a,depth:0,component_id:1,cluster_id:1},{gid:b,depth:1,component_id:1,cluster_id:1},{gid:c,depth:0,component_id:2,cluster_id:2}],edges:[{src:a,dst:b}]};
test('exact IDs, direction and isolated nodes survive filtering',()=>{
 assert.equal(visibleGraph(data,null,'all','all').nodes.length,3);
 assert.deepEqual(visibleGraph(data,a,'neighborhood','all').nodes.map(n=>n.gid),[a,b]);
 assert.equal(visibleGraph(data,c,'neighborhood','all').nodes.length,1);
 assert.equal(visibleGraph(data,null,'all','2').edges.length,0);
 assert.equal(layout(data.nodes).size,3);
});
test('local dictionaries cover both languages and all roles',()=>{
 assert.deepEqual(Object.keys(dictionaries.en).sort(),Object.keys(dictionaries.ru).sort());
 assert.deepEqual(Object.keys(roles.en).sort(),Object.keys(roles.ru).sort());
 assert.deepEqual(Object.keys(featureText.en).sort(),Object.keys(featureText.ru).sort());
 assert.match(evidence({role:'peripheral',is_depth4_boundary:true},'ru'),/граница/);
});
test('cluster filtering uses communities independently of component IDs',()=>{
 const split={...data,nodes:data.nodes.map((n,i)=>({...n,component_id:1,cluster_id:i+1}))};
 assert.deepEqual(visibleGraph(split,null,'all','2').nodes.map(n=>n.gid),[b]);
 const positions=layout(split.nodes,null,split.edges);
 assert.equal(positions.size,3);
 assert.ok([...positions.values()].every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)));
});

test('layout is deterministic, finite, bounded and preserves all members',()=>{
 for(const count of [0,1,2,270,1877,2248]){
  const nodes=Array.from({length:count},(_,i)=>({gid:String(i+1).padStart(18,'0'),cluster_id:1,depth:i%5}));
  const edges=nodes.slice(1).map((n,i)=>({src:nodes[Math.floor(i/3)].gid,dst:n.gid}));
  const start=performance.now(),positions=layout(nodes,null,edges);
  assert.equal(positions.size,count);
  assert.ok(performance.now()-start<5000,'Layout must remain responsive in a worker');
  assert.ok([...positions.values()].every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)));
  for(const [w,h] of [[0,0],[320,480],[1100,700]]){
   const camera=fitViewport(positions,w,h,true);assert.ok(camera.k>0&&Number.isFinite(camera.k));
   if(w>0)for(const p of positions.values()){
    assert.ok(p.x*camera.k+camera.x>=0&&p.x*camera.k+camera.x<=w);
    assert.ok(p.y*camera.k+camera.y>=0&&p.y*camera.k+camera.y<=h);
   }
  }
  if(count<300)assert.deepEqual([...positions].sort(),[...layout([...nodes].reverse(),null,[...edges].reverse())].sort());
 }
});

test('neighborhood traversal cannot shortcut outside a filtered community',()=>{
 const fixture={nodes:[{gid:a,cluster_id:1},{gid:b,cluster_id:2},{gid:c,cluster_id:1}],edges:[{src:a,dst:b},{src:b,dst:c}]};
 assert.deepEqual(visibleGraph(fixture,a,'neighborhood','1',null,4).nodes.map(n=>n.gid),[a]);
});
test('directed multi-hop seed tracing and previous-account context',()=>{
 const chain={...data,edges:[{src:a,dst:b},{src:b,dst:c}]};
 assert.deepEqual(visibleGraph(chain,a,'neighborhood','all',null,1,'out').nodes.map(n=>n.gid),[a,b]);
 assert.equal(visibleGraph(chain,a,'neighborhood','all',null,2,'out').nodes.length,3);
 assert.equal(visibleGraph(chain,a,'neighborhood','all',null,4,'in').nodes.length,1);
 assert.equal(visibleGraph(chain,c,'neighborhood','all',a,1,'out').nodes.length,2);
 assert.equal(edgeColor(chain.edges[0],b),edgeColors.incoming);
 assert.equal(edgeColor(chain.edges[1],b),edgeColors.outgoing);
 const p={x:0,y:0},q={x:100,y:0};
 assert.notEqual(curve(p,q,a,b).y,curve(q,p,b,a).y);
 assert.equal(layout(data.nodes,a).get(a).x,0);
});
