const test=require('node:test'),assert=require('node:assert/strict');
require('./core.js');
const {bake,zip,crc}=globalThis.VinylCore;
const opt={zone:'both',scale:100,x:0,y:0,rotation:0,opacity:100,readable:true};
const model={bounds:[[-1,-1,0],[1,1,2]],triangles:[
 [1,-1,1,0,0,1, 1,1,0,1,1, 1,1,2,1,0],
 [1,-1,1,0,0,1, 1,1,2,1,0, -1,1,2,0,0]
]};
const red={width:2,height:2,data:new Uint8ClampedArray([255,0,0,255,255,0,0,255,255,0,0,255,255,0,0,255])};
test('UV rasterization produces colored pixels and respects surface selection and opacity',()=>{
 const a=bake(model,red,opt,32);assert.ok(a.filter((v,i)=>i%4===3&&v===255).length>500);
 const p=(16*32+16)*4;assert.deepEqual([...a.slice(p,p+4)],[255,0,0,255]);
 assert.equal(bake(model,red,{...opt,zone:'right'},32).some(Boolean),false);
 assert.equal(bake(model,red,{...opt,zone:'top'},32).some(Boolean),false);
 assert.equal(bake(model,red,{...opt,opacity:50},32)[p+3],128);
 assert.equal(bake(model,red,{...opt,x:300},32).some(Boolean),false);
});
test('ZIP contains matching CRC, filenames and central directory',async()=>{
 const bytes=new TextEncoder().encode('123456789');assert.equal(crc(bytes),0xcbf43926);
 const b=Buffer.from(await zip([{name:'game/CARS/240SX/VINYLS/240SX_CONTEST_01.png',data:bytes}]).arrayBuffer());
 assert.equal(b.readUInt32LE(0),0x04034b50);assert.equal(b.readUInt32LE(14),0xcbf43926);
 assert.equal(b.readUInt32LE(b.length-22),0x06054b50);assert.equal(b.readUInt16LE(b.length-12),1);
});
