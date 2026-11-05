const test=require('node:test'),assert=require('node:assert/strict');require('./decals.js');const D=globalThis.Decals;
const model={bounds:[[-1,-1,0],[1,1,2]],triangles:[[1,-1,1,0,0,1,1,1,0,1,1,1,1,2,1,0],[1,-1,1,0,0,1,1,1,2,1,0,-1,1,2,0,0]]};
const image=color=>({pixels:{width:2,height:2,data:new Uint8ClampedArray([...color,...color,...color,...color])}});
const assets={red:image([255,0,0,255]),blue:image([0,0,255,255])};
const layer=(assetId='red')=>({id:'layer',assetId,name:'Decal',kind:'decal',visible:true,opacity:100,position:[0,1,1],normal:[0,1,0],tangent:[-1,0,0],width:2,height:2,depth:.2,rotation:0,flipX:false,flipY:false});

test('steep window returns receive vinyl inside the projection volume',()=>{
 const steep={...layer(),normal:D.norm([0,.1,1]),width:3,height:3,depth:3};
 const pixels=D.bake(model,[steep],assets,32);
 assert.equal(pixels[(16*32+16)*4+3],255);
 assert.equal(D.bake(model,[{...steep,position:[0,1,5],depth:.1}],assets,32).some(Boolean),false);
});

test('transparent samples on shared UV surfaces do not erase painted samples',()=>{
 const shared=JSON.parse(JSON.stringify(model));
 for(const t of model.triangles){const near=t.slice();for(const k of [1,6,11])near[k]+=.8;for(const k of [2,7,12])near[k]+=.05;shared.triangles.push(near);}
 const cutout={pixels:{width:2,height:1,data:new Uint8ClampedArray([255,0,0,255,0,0,0,0])}};
 const l={...layer('cutout'),position:[0,1.05,1],tangent:[1,0,0],width:2,height:3};
 const pixels=D.bake(shared,[l],{cutout},32);
 assert.ok(pixels[(16*32+24)*4+3]>0,'near transparent triangle must not mask the farther painted triangle');
});

test('UV island padding covers filtered seams without expanding artwork within the surface',()=>{
 const island=JSON.parse(JSON.stringify(model));
 for(const t of island.triangles)for(const k of [4,5,9,10,14,15])t[k]=.2+t[k]*.6;
 const at=(p,x,y)=>[...p.slice((y*64+x)*4,(y*64+x)*4+4)];
 const full=D.bake(island,[{...layer(),width:3,height:3,opacity:50}],assets,64);
 // The surface starts at 12.8 texels: bilinear filtering also reads texel 12.
 assert.deepEqual(at(full,12,32),[255,0,0,128]);
 assert.deepEqual(at(full,12,12),[255,0,0,128]);
 assert.equal(at(full,5,32)[3],0);
 const narrow=D.bake(island,[{...layer(),width:.5}],assets,64);
 assert.equal(at(narrow,20,32)[3],0,'transparent paintable pixels stay transparent');
 assert.equal(at(narrow,12,32)[3],0,'an unpainted island edge stays unpainted');
 assert.equal(at(narrow,32,32)[3],255);
});
test('ray placement hits the true surface and rejects misses',()=>{const h=D.hit(model,[0,5,1],[0,-1,0]);assert.deepEqual(h.position,[0,1,1]);assert.equal(h.skin,true);assert.ok(D.dot(h.normal,[0,1,0])>.999);assert.equal(D.hit(model,[10,5,1],[0,-1,0]),null);});
test('3D decal is upright, clipped by depth, and 512 RGBA export is full sized',()=>{const a=layer(),b=D.bake(model,[a],assets,512);assert.equal(b.length,512*512*4);assert.deepEqual([...b.slice((256*512+256)*4,(256*512+256)*4+4)],[255,0,0,255]);assert.equal(D.bake(model,[{...a,position:[0,-1,1]}],assets,16).some(Boolean),false);const uv=D.coordinates(a,[0,1,1.5]);assert.equal(uv[1],.25);});
test('layer ordering, opacity, visibility and independent height work',()=>{const red=layer(),blue={...layer('blue'),id:'blue',opacity:50};const sample=a=>[...D.bake(model,a,assets,16).slice((8*16+8)*4,(8*16+8)*4+4)];assert.deepEqual(sample([red,blue]),[128,0,128,255]);assert.deepEqual(sample([blue,red]),[255,0,0,255]);assert.deepEqual(sample([red,{...blue,visible:false}]),[255,0,0,255]);assert.equal(D.bake(model,[{...red,height:.2}],assets,16)[(2*16+8)*4+3],0);});
test('transfer creates independent normalized placement on the destination',()=>{const target=JSON.parse(JSON.stringify(model));target.bounds=[[-2,-2,0],[2,2,4]];for(const t of target.triangles)for(const i of [1,6,11])for(let k=0;k<3;k++)t[i+k]*=2;const a=layer(),b=D.transfer(a,model,target);assert.deepEqual(b.position,[0,2,2]);assert.equal(b.width,4);assert.equal(b.height,4);b.position[0]=1;assert.deepEqual(a.position,[0,1,1]);});
test('project validation rejects corrupt references and transforms without changing valid layers',()=>{const a=layer();assert.deepEqual(D.validateLayer(a,assets),a);assert.throws(()=>D.validateLayer({...a,assetId:'missing'},assets));assert.throws(()=>D.validateLayer({...a,width:NaN},assets));assert.throws(()=>D.validateLayer({...a,normal:[0,0,0]},assets));});
test('opposite side preserves vertical orientation and independently mirrors artwork',()=>{const l={...layer(),rotation:31,mirrorSide:true,mirrorTexture:true};const p=[.4,1,1.3],q=D.reflect(p),a=D.coordinates(l,p),b=D.coordinates(D.opposite(l),q);assert.ok(Math.abs(a[0]-(1-b[0]))<1e-8);assert.ok(Math.abs(a[1]-b[1])<1e-8);assert.equal(D.opposite(l).flipX,true);assert.equal(D.opposite({...l,mirrorTexture:false}).flipX,false);assert.deepEqual(D.validateLayer(l,assets),l);assert.throws(()=>D.validateLayer({...l,mirrorSide:'yes'},assets));});
test('opposite copy exports to both UV islands without doubling opacity',()=>{const both=JSON.parse(JSON.stringify(model));for(const t of both.triangles)for(const k of [4,9,14])t[k]*=.5;const other=both.triangles.map(t=>{t=t.slice();for(const k of [2,7,12])t[k]*=-1;for(const k of [4,9,14])t[k]+=.5;return t;});both.triangles.push(...other);const l={...layer(),opacity:50,mirrorSide:true};const at=(pixels,x)=>[...pixels.slice((8*32+x)*4,(8*32+x)*4+4)];const on=D.bake(both,[l],assets,32),off=D.bake(both,[{...l,mirrorSide:false}],assets,32);assert.deepEqual(at(on,8),[255,0,0,128]);assert.deepEqual(at(on,24),[255,0,0,128]);assert.equal(at(off,24)[3],0);const overlap={...l,position:[0,0,1],depth:4};assert.equal(at(D.bake(both,[overlap],assets,32),8)[3],128);});
test('camera and decal axes agree without reflecting readable artwork',()=>{const fs=require('node:fs'),vm=require('node:vm'),sandbox={window:{},Decals:D};vm.runInNewContext(fs.readFileSync(require.resolve('./viewer.js'),'utf8'),sandbox);const Viewer=sandbox.window.CarViewer;for(const yaw of [0,.65,Math.PI,-Math.PI/2]){const camera=Viewer.prototype.axes.call({yaw,pitch:.32});assert.ok(D.dot(D.cross(camera.right,camera.up),camera.forward)>.999);const l={...layer(),...D.basis(camera.forward,camera.right)};const [u,v]=D.axes(l);assert.ok(D.dot(u,camera.right)>.999);assert.ok(D.dot(v,camera.up)>.999);const p=D.add(l.position,D.add(D.mul(camera.right,.3),D.mul(camera.up,.3)));const uv=D.coordinates(l,p);assert.ok(uv[0]>.5&&uv[1]<.5);}});

test('preview cache matches export after moves, reorder, visibility and image changes',()=>{
 const cache=new Map(),ls=[layer(),{...layer('blue'),id:'second',opacity:50,width:1}],a={...assets};
 const check=()=>assert.deepEqual(D.bake(model,ls,a,64,cache),D.bake(model,ls,a,64));
 check();const unchanged=cache.get('second').pixels;
 ls[0].position[0]+=.3;check();assert.equal(cache.get('second').pixels,unchanged);
 ls.reverse();check();ls[0].visible=false;check();assert(!cache.has('second'));
 ls[0].visible=true;a.blue=image([0,255,0,255]);check();ls.pop();check();assert.equal(cache.size,1);
 assert.deepEqual(D.bake(model,ls,a,32,cache),D.bake(model,ls,a,32));
});
