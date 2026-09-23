import {expect} from '@playwright/test';
import {visibleGraph,layout,fitViewport} from '../src/graph.js';

export async function settled(page){
 await expect(page.locator('canvas')).toHaveAttribute('data-layout-state','ready',{timeout:15000});
}

export async function nodePoints(page,data,gid){
 await settled(page);
 const box=await page.locator('canvas').boundingBox();
 const graph=visibleGraph(data,gid,'neighborhood','all');
 const positions=layout(graph.nodes,gid,graph.edges),v=fitViewport(positions,box.width,box.height,true);
 return {box,points:graph.nodes.map(n=>({n,x:positions.get(n.gid).x*v.k+v.x,y:positions.get(n.gid).y*v.k+v.y}))};
}
