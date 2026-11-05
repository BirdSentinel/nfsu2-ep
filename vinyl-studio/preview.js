/* Keep texture rasterization off the UI thread. During edits render a cheap
 * preview, then refine once input settles. Export always uses the original bake. */
class VinylPreview {
 constructor(draw,error){
  this.draw=draw;this.error=error;this.revision=0;this.generation=0;this.busy=false;this.assetsSent=new Map();
  const source=Decals.workerSource()+`
   let model, assets;const cache=new Map();
   onmessage=({data:m})=>{try{
    if(m.model){model=m.model;cache.clear();}if(m.assets)assets=m.assets;
    const pixels=Decals.bake(model,m.layers,assets,m.size,m.size===256?cache:null);
    postMessage({revision:m.revision,generation:m.generation,size:m.size,pixels},[pixels.buffer]);
   }catch(e){postMessage({revision:m.revision,generation:m.generation,error:e.message});}};`;
  const url=URL.createObjectURL(new Blob([source],{type:'text/javascript'}));
  try{this.worker=new Worker(url);this.worker.onmessage=e=>this.complete(e.data);this.worker.onerror=e=>{e.preventDefault();this.fallback();};}
  catch{this.worker=null;}finally{URL.revokeObjectURL(url);}
 }
 request(model,layers,assets){
  if(model!==this.model||assets!==this.assets){this.generation++;this.model=model;this.assets=assets;}
  this.layers=layers;this.revision++;
  this.pending={revision:this.revision,generation:this.generation,size:256};
  clearTimeout(this.refine);
  this.refine=setTimeout(()=>{this.pending={revision:this.revision,generation:this.generation,size:1024};this.schedule();},220);
  this.schedule();
 }
 schedule(){if(this.frame||this.busy)return;this.frame=requestAnimationFrame(()=>{this.frame=0;this.dispatch();});}
 dispatch(){
  if(this.busy||!this.pending)return;
  const task=this.pending;this.pending=null;this.busy=true;
  task.layers=JSON.parse(JSON.stringify(this.layers));
  if(!this.worker){
   // Older browsers may prohibit workers; retain a responsive reduced preview.
   try{this.complete({...task,pixels:Decals.bake(this.model,task.layers,this.assets,task.size)});}catch(e){this.complete({...task,error:e.message});}return;
  }
  if(this.sentModel!==this.model){task.model=this.model;this.sentModel=this.model;}
  const entries=Object.entries(this.assets);
  if(entries.length!==this.assetsSent.size||entries.some(([id,a])=>this.assetsSent.get(id)!==a.pixels)){
   task.assets=Object.fromEntries(entries.map(([id,a])=>[id,{pixels:a.pixels}]));this.assetsSent=new Map(entries.map(([id,a])=>[id,a.pixels]));
  }
  try{this.worker.postMessage(task);}catch(e){this.pending=task;this.fallback();}
 }
 complete(result){
  this.busy=false;
  // A draft may trail the pointer by one frame; an obsolete full-size render
  // must never replace it. Switching cars/projects invalidates both kinds.
  if(result.generation===this.generation&&(result.size===256||result.revision===this.revision)){
   if(result.error)this.error(result.error);else this.draw(result.pixels,result.size);
  }
  this.schedule();
 }
 fallback(){this.worker?.terminate();this.worker=null;this.busy=false;this.pending={revision:this.revision,generation:this.generation,size:256};this.schedule();}
}
window.VinylPreview=VinylPreview;
