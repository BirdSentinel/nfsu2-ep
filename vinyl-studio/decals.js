(function install(root){
'use strict';
const add=(a,b)=>a.map((v,i)=>v+b[i]),sub=(a,b)=>a.map((v,i)=>v-b[i]),mul=(a,s)=>a.map(v=>v*s),dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],norm=a=>{const n=Math.hypot(...a);return n>1e-10?mul(a,1/n):[0,0,1];};
function basis(normal,right=[1,0,0]){const n=norm(normal);let u=sub(right,mul(n,dot(right,n)));if(Math.hypot(...u)<.001)u=cross([0,1,0],n);u=norm(u);return {normal:n,tangent:u};}
function axes(l){const u=norm(l.tangent),v=norm(cross(l.normal,u)),a=l.rotation*Math.PI/180;return [add(mul(u,Math.cos(a)),mul(v,Math.sin(a))),add(mul(u,-Math.sin(a)),mul(v,Math.cos(a)))];}
// Cars use X for length and Y for width; reflect across the Y=0 center plane.
const reflect=p=>[p[0],-p[1],p[2]];
function opposite(l){return {...l,position:reflect(l.position),normal:reflect(l.normal),tangent:mul(reflect(l.tangent),-1),rotation:-l.rotation,flipX:l.mirrorTexture?!l.flipX:l.flipX,mirrorSide:false};}
function instances(l){return l.kind==='decal'&&l.mirrorSide?[l,opposite(l)]:[l];}
function hit(model,origin,direction,skinOnly=false){let best=null;
 for(let index=0;index<model.triangles.length;index++){const t=model.triangles[index];if(skinOnly&&!t[0])continue;const a=t.slice(1,4),b=t.slice(6,9),c=t.slice(11,14),e1=sub(b,a),e2=sub(c,a),p=cross(direction,e2),det=dot(e1,p);if(Math.abs(det)<1e-9)continue;const inv=1/det,s=sub(origin,a),u=dot(s,p)*inv;if(u<0||u>1)continue;const q=cross(s,e1),v=dot(direction,q)*inv;if(v<0||u+v>1)continue;const distance=dot(e2,q)*inv;if(distance<0||best&&distance>=best.distance)continue;let n=norm(cross(e1,e2));if(dot(n,direction)>0)n=mul(n,-1);best={position:add(origin,mul(direction,distance)),normal:n,distance,skin:!!t[0],triangle:index};}
 return best;
}
function closest(model,point,preferred){let best=null;
 for(const t of model.triangles){if(!t[0])continue;const a=t.slice(1,4),b=t.slice(6,9),c=t.slice(11,14),ab=sub(b,a),ac=sub(c,a);let n=norm(cross(ab,ac));if(dot(n,preferred)<0)n=mul(n,-1);const p=sub(point,mul(n,dot(sub(point,a),n))),ap=sub(p,a);const aa=dot(ab,ab),bb=dot(ac,ac),cc=dot(ab,ac),den=aa*bb-cc*cc;if(Math.abs(den)<1e-12)continue;const u=(bb*dot(ap,ab)-cc*dot(ap,ac))/den,v=(aa*dot(ap,ac)-cc*dot(ap,ab))/den;const candidates=[];
  if(u>=0&&v>=0&&u+v<=1)candidates.push(p);
  for(const [s,e] of [[a,b],[b,c],[c,a]]){const d=sub(e,s),f=Math.max(0,Math.min(1,dot(sub(point,s),d)/(dot(d,d)||1)));candidates.push(add(s,mul(d,f)));}
  for(const q of candidates){const d=dot(sub(point,q),sub(point,q));if(!best||d<best.distance)best={position:q,normal:n,distance:d};}
 }return best;
}
function transfer(l,from,to){const result=JSON.parse(JSON.stringify(l));if(l.kind==='uv')return result;const scale=from.bounds[0].map((v,k)=>(to.bounds[1][k]-to.bounds[0][k])/(from.bounds[1][k]-v));const p=l.position.map((v,k)=>to.bounds[0][k]+(v-from.bounds[0][k])*scale[k]);const n=norm(l.normal.map((v,k)=>v/scale[k]));const snap=closest(to,p,n);if(!snap)throw Error('The target model has no paintable surface.');Object.assign(result,{position:snap.position},basis(snap.normal,l.tangent.map((v,k)=>v*scale[k])));const [u,v]=axes(l);result.width*=Math.hypot(...u.map((x,k)=>x*scale[k]));result.height*=Math.hypot(...v.map((x,k)=>x*scale[k]));result.depth*=Math.max(...scale);return result;}
function sample(img,u,v){if(u<0||u>1||v<0||v>1)return [0,0,0,0];const x=u*(img.width-1),y=v*(img.height-1),ix=Math.floor(x),iy=Math.floor(y),fx=x-ix,fy=y-iy,a=[0,0,0,0];for(let dy=0;dy<2;dy++)for(let dx=0;dx<2;dx++){const p=(Math.min(img.height-1,iy+dy)*img.width+Math.min(img.width-1,ix+dx))*4,w=(dx?fx:1-fx)*(dy?fy:1-fy),alpha=img.data[p+3]/255;a[3]+=alpha*w;for(let k=0;k<3;k++)a[k]+=img.data[p+k]*alpha*w;}return a;}
function coordinates(layer,point){const [u,v]=axes(layer),d=sub(point,layer.position);return [dot(d,u)/layer.width+.5,.5-dot(d,v)/layer.height,dot(d,layer.normal)];}
function contains(layer,point,img){if(layer.kind==='uv')return false;const [u,v,d]=coordinates(layer,point);return Math.abs(d)<=layer.depth/2&&sample(img,layer.flipX?1-u:u,layer.flipY?1-v:v)[3]>.05;}
// Texture filtering samples beyond UV island edges. Extend only into unused
// atlas space, never into transparent artwork on a paintable surface.
const gutterCache=new WeakMap();
function gutters(model,size){
 let sizes=gutterCache.get(model);if(!sizes){sizes=new Map();gutterCache.set(model,sizes);}if(sizes.has(size))return sizes.get(size);
 let owners=new Int32Array(size*size);owners.fill(-1);
 for(const t of model.triangles){if(!t[0])continue;const [p,q,r]=[4,9,14].map(i=>[t[i]*size,t[i+1]*size]);
  const den=(q[1]-r[1])*(p[0]-r[0])+(r[0]-q[0])*(p[1]-r[1]);if(Math.abs(den)<1e-9)continue;
  const x0=Math.max(0,Math.floor(Math.min(p[0],q[0],r[0]))),x1=Math.min(size-1,Math.ceil(Math.max(p[0],q[0],r[0]))),y0=Math.max(0,Math.floor(Math.min(p[1],q[1],r[1]))),y1=Math.min(size-1,Math.ceil(Math.max(p[1],q[1],r[1])));
  for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){const a=((q[1]-r[1])*(x+.5-r[0])+(r[0]-q[0])*(y+.5-r[1]))/den,b=((r[1]-p[1])*(x+.5-r[0])+(p[0]-r[0])*(y+.5-r[1]))/den;if(Math.min(a,b,1-a-b)>=-.00001)owners[y*size+x]=y*size+x;}
 }
 const covered=owners.slice();
 const radius=Math.max(4,Math.round(size/128));for(let pass=0;pass<radius;pass++){const next=owners.slice();for(let y=0;y<size;y++)for(let x=0;x<size;x++){const at=y*size+x;if(covered[at]>=0)continue;let best=owners[at],distance=best<0?Infinity:(best%size-x)**2+(Math.floor(best/size)-y)**2;
  for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){if(x+dx<0||x+dx>=size||y+dy<0||y+dy>=size)continue;const owner=owners[(y+dy)*size+x+dx];if(owner<0)continue;const d=(owner%size-x)**2+(Math.floor(owner/size)-y)**2;if(d<=radius*radius&&d<distance){best=owner;distance=d;}}
  next[at]=best;}owners=next;}
 const pairs=[];for(let at=0;at<owners.length;at++)if(covered[at]<0&&owners[at]>=0)pairs.push(at*4,owners[at]*4);
 sizes.set(size,pairs);return pairs;
}
const geometryCache=new WeakMap();
function geometry(model){let list=geometryCache.get(model);if(!list){list=model.triangles.filter(t=>t[0]).map(t=>{const verts=[t.slice(1,6),t.slice(6,11),t.slice(11,16)],a=verts[0],b=verts[1],c=verts[2];return {verts,normal:norm(cross(sub(b.slice(0,3),a),sub(c.slice(0,3),a)))};});geometryCache.set(model,list);}return list;}
function bake(model,layers,assets,size=512,cache=null){const output=new Float32Array(size*size*4);
 for(const layer of layers){if(!layer.visible||layer.opacity<=0)continue;const img=assets[layer.assetId]?.pixels;if(!img)throw Error('Missing decal image: '+layer.assetId);const key=cache?JSON.stringify(layer):null,old=cache?.get(layer.id);let pixels;
  if(old&&old.key===key&&old.img===img&&old.model===model&&old.size===size)pixels=old.pixels;else{
  pixels=new Float32Array(size*size*4);const depth=new Float32Array(size*size);depth.fill(Infinity);
  if(layer.kind==='uv'){for(let y=0;y<size;y++)for(let x=0;x<size;x++)pixels.set(sample(img,(x+.5)/size,(y+.5)/size),(y*size+x)*4);}
  else{const projections=instances(layer);for(const layer of projections){
   const [uaxis,vaxis]=axes(layer);
   // Curved window returns can be almost edge-on to the projection. The
   // explicit projection depth clips them; an angle cutoff leaves bare spots.
   for(const {verts,normal} of geometry(model)){if(Math.abs(dot(normal,layer.normal))<1e-6)continue;
    const local=verts.map(p=>{const d=sub(p.slice(0,3),layer.position);return [dot(d,uaxis)/layer.width+.5,.5-dot(d,vaxis)/layer.height,dot(d,layer.normal)];});
    if([0,1].some(k=>Math.max(...local.map(v=>v[k]))<0||Math.min(...local.map(v=>v[k]))>1)||Math.min(...local.map(v=>v[2]))>layer.depth/2||Math.max(...local.map(v=>v[2]))< -layer.depth/2)continue;
    const [p,q,r]=verts.map(v=>[v[3]*size,v[4]*size]),den=(q[1]-r[1])*(p[0]-r[0])+(r[0]-q[0])*(p[1]-r[1]);if(Math.abs(den)<1e-9)continue;
    const x0=Math.max(0,Math.floor(Math.min(p[0],q[0],r[0]))),x1=Math.min(size-1,Math.ceil(Math.max(p[0],q[0],r[0]))),y0=Math.max(0,Math.floor(Math.min(p[1],q[1],r[1]))),y1=Math.min(size-1,Math.ceil(Math.max(p[1],q[1],r[1])));
    for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){const wa=((q[1]-r[1])*(x+.5-r[0])+(r[0]-q[0])*(y+.5-r[1]))/den,wb=((r[1]-p[1])*(x+.5-r[0])+(p[0]-r[0])*(y+.5-r[1]))/den,wc=1-wa-wb;if(Math.min(wa,wb,wc)<-.00001)continue;const v=local[0].map((a,k)=>a*wa+local[1][k]*wb+local[2][k]*wc),at=y*size+x,d=Math.abs(v[2]);if(d>layer.depth/2||d>=depth[at])continue;const rgba=sample(img,layer.flipX?1-v[0]:v[0],layer.flipY?1-v[1]:v[1]);if(rgba[3]<=0)continue;pixels.set(rgba,at*4);depth[at]=d;}
   }
  }
  }
  if(cache)cache.set(layer.id,{key,img,model,size,pixels});}
  const opacity=layer.opacity/100;for(let p=0;p<output.length;p+=4){const alpha=pixels[p+3]*opacity;if(!alpha)continue;for(let k=0;k<3;k++)output[p+k]=pixels[p+k]*opacity+output[p+k]*(1-alpha);output[p+3]=alpha+output[p+3]*(1-alpha);}
 }
 if(cache){const ids=new Set(layers.filter(l=>l.visible&&l.opacity>0).map(l=>l.id));for(const id of cache.keys())if(!ids.has(id))cache.delete(id);}
 const out=new Uint8ClampedArray(output.length);for(let p=0;p<out.length;p+=4){const a=output[p+3];if(a){for(let k=0;k<3;k++)out[p+k]=output[p+k]/a;out[p+3]=a*255;}}
 const padding=gutters(model,size);for(let i=0;i<padding.length;i+=2){const dst=padding[i],src=padding[i+1];if(!out[dst+3])out.set(out.subarray(src,src+4),dst);}return out;
}
function validateLayer(l,assets){
 if(!l||typeof l.id!=='string'||l.id.length>100||!Object.hasOwn(assets,l.assetId)||typeof l.name!=='string'||l.name.length>200||typeof l.visible!=='boolean'||!Number.isFinite(l.opacity)||l.opacity<0||l.opacity>100)throw Error('Invalid layer in project.');
 const out={id:l.id,assetId:l.assetId,name:l.name,visible:l.visible,opacity:l.opacity,kind:l.kind};if(l.kind==='uv')return out;if(l.kind!=='decal')throw Error('Unknown layer type.');
 for(const key of ['position','normal','tangent'])if(!Array.isArray(l[key])||l[key].length!==3||!l[key].every(v=>Number.isFinite(v)&&Math.abs(v)<100))throw Error('Invalid 3D transform.');
 if(Math.hypot(...l.normal)<.1||Math.hypot(...l.tangent)<.1||Math.abs(dot(norm(l.normal),norm(l.tangent)))>.01)throw Error('Invalid decal axes.');
 for(const key of ['width','height','depth'])if(!Number.isFinite(l[key])||l[key]<.005||l[key]>30)throw Error('Invalid decal dimensions.');
 if(!Number.isFinite(l.rotation)||Math.abs(l.rotation)>36000||typeof l.flipX!=='boolean'||typeof l.flipY!=='boolean')throw Error('Invalid decal settings.');
 if(Math.abs(Math.hypot(...l.normal)-1)>.001||Math.abs(Math.hypot(...l.tangent)-1)>.001)throw Error('Decal axes must have unit length.');
 for(const key of ['mirrorSide','mirrorTexture'])if(l[key]!==undefined){if(typeof l[key]!=='boolean')throw Error('Invalid opposite-side settings.');out[key]=l[key];}
 return {...out,position:[...l.position],normal:[...l.normal],tangent:[...l.tangent],width:l.width,height:l.height,depth:l.depth,rotation:l.rotation,flipX:l.flipX,flipY:l.flipY};
}
root.Decals={workerSource:()=>`(${install.toString()})(self);`,add,sub,mul,dot,cross,norm,basis,axes,reflect,opposite,instances,hit,closest,transfer,coordinates,contains,bake,validateLayer};
})(typeof window==='undefined'?globalThis:window);
