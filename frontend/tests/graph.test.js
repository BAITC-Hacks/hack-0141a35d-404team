import test from 'node:test';
import assert from 'node:assert/strict';
import {visibleGraph,layout} from '../src/graph.js';
import {dictionaries,roles,evidence} from '../src/i18n.js';

const a='100000000011452101',b='100000000011452102',c='100000000011452103';
const data={nodes:[{gid:a,depth:0,component_id:1},{gid:b,depth:1,component_id:1},{gid:c,depth:0,component_id:2}],edges:[{src:a,dst:b}]};
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
 assert.match(evidence({role:'peripheral',is_depth4_boundary:true},'ru'),/граница/);
});
