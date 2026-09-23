import {layout} from './graph.js';
self.onmessage=({data})=>{
 try{
  self.postMessage({id:data.id,positions:[...layout(data.nodes,data.anchor,data.edges)]});
 }catch{
  self.postMessage({id:data.id,error:true});
 }
};
