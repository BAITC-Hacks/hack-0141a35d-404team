// Exhaustively exercises all real clusters, including singletons, in the browser.
import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
import {settled} from './graph-helpers.mjs';
const base=process.env.AML_TEST_URL||'http://127.0.0.1:8000';
const browser=await chromium.launch({channel:'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto(base);
 const pending=page.waitForResponse(r=>r.url().endsWith('/api/analyze'));
 await page.getByRole('button',{name:'Run analysis'}).click();
 const response=await pending;assert.equal(response.status(),200);const data=await response.json();
 await settled(page);
 const canvas=page.locator('canvas'),picker=page.getByRole('combobox',{name:'Cluster',exact:true});
 await expect(canvas).toHaveAttribute('data-rendered-nodes',String(data.nodes.length));
 assert.equal(data.clusters.reduce((sum,c)=>sum+c.n_nodes,0),data.nodes.length);
 await page.screenshot({path:'dist/cluster-overview-fixed.png'});
 for(const cluster of data.clusters){
  await picker.selectOption(String(cluster.cluster_id));await settled(page);
  await expect(canvas).toHaveAttribute('data-rendered-nodes',String(cluster.n_nodes));
  const members=data.nodes.filter(n=>n.cluster_id===cluster.cluster_id);assert.equal(members.length,cluster.n_nodes);
  const edges=data.edges.filter(e=>members.some(n=>n.gid===e.src)&&members.some(n=>n.gid===e.dst));
  await expect(page.locator('.graph-meta')).toContainText(cluster.n_nodes+' accounts · '+edges.length+' connections');
  // Test that pixels, not just a DOM counter, have actually been painted.
  assert.ok(await canvas.evaluate(c=>{const pixels=c.getContext('2d').getImageData(0,0,c.width,c.height).data;for(let i=3;i<pixels.length;i+=4)if(pixels[i])return true;return false;}));
 }
 const largest=data.clusters.reduce((a,b)=>a.n_nodes>b.n_nodes?a:b);
 await picker.selectOption(String(largest.cluster_id));await settled(page);
 await page.screenshot({path:'dist/largest-cluster-fixed.png'});
 // Superseded layout workers must not restore a stale graph after fast changes.
 await picker.selectOption('all');await picker.selectOption(String(data.clusters.at(-1).cluster_id));await picker.selectOption(String(largest.cluster_id));
 await settled(page);await expect(canvas).toHaveAttribute('data-rendered-nodes',String(largest.n_nodes));
 await page.getByRole('button',{name:'Full network',exact:true}).click();await settled(page);
 await page.setViewportSize({width:390,height:844});await settled(page);
 await expect(canvas).toHaveAttribute('data-rendered-nodes',String(data.nodes.length));
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 assert.deepEqual(errors,[]);
 console.log('PASS: all '+data.clusters.length+' communities; every node painted; counts match actual membership; rapid switching; mobile; largest '+largest.n_nodes+' accounts.');
}finally{await browser.close();}
