/* Original UV triangle rasterizer. No network or third-party runtime. */
(function(root){
  'use strict';
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  function bake(model, image, opt, size=512){
    const out=new Uint8ClampedArray(size*size*4), [lo,hi]=model.bounds;
    const length=hi[0]-lo[0], height=hi[2]-lo[2], width=hi[1]-lo[1];
    const span=length*opt.scale/100, angle=opt.rotation*Math.PI/180, cs=Math.cos(angle),sn=Math.sin(angle);
    if(!(span>0)||!image.width||!image.height)throw Error('Invalid image dimensions.');
    const aspect=image.width/image.height;
    for(const t of model.triangles){
      if(!t[0])continue;
      const a=t.slice(1,6),b=t.slice(6,11),c=t.slice(11,16);
      const n=cross(b.slice(0,3).map((v,i)=>v-a[i]),c.slice(0,3).map((v,i)=>v-a[i]));
      const norm=Math.hypot(...n), cy=(a[1]+b[1]+c[1])/3,cz=(a[2]+b[2]+c[2])/3;
      if(!norm)continue;
      const top=opt.zone==='top';
      if(top ? Math.abs(n[2])/norm<.5||cz<lo[2]+height*.4 : Math.abs(n[1])/norm<.45||Math.abs(cy)<width*.15)continue;
      if(opt.zone==='left'&&cy<0||opt.zone==='right'&&cy>=0)continue;
      const px=[a,b,c].map(v=>[v[3]*size,v[4]*size]);
      const [p,q,r]=px,den=(q[1]-r[1])*(p[0]-r[0])+(r[0]-q[0])*(p[1]-r[1]);
      if(Math.abs(den)<1e-8)continue;
      const xmin=Math.max(0,Math.floor(Math.min(p[0],q[0],r[0]))),xmax=Math.min(size-1,Math.ceil(Math.max(p[0],q[0],r[0])));
      const ymin=Math.max(0,Math.floor(Math.min(p[1],q[1],r[1]))),ymax=Math.min(size-1,Math.ceil(Math.max(p[1],q[1],r[1])));
      for(let y=ymin;y<=ymax;y++)for(let x=xmin;x<=xmax;x++){
        const wa=((q[1]-r[1])*(x+.5-r[0])+(r[0]-q[0])*(y+.5-r[1]))/den;
        const wb=((r[1]-p[1])*(x+.5-r[0])+(p[0]-r[0])*(y+.5-r[1]))/den,wc=1-wa-wb;
        if(wa<-.00001||wb<-.00001||wc<-.00001)continue;
        const pos=[0,1,2].map(k=>a[k]*wa+b[k]*wb+c[k]*wc);
        let u=(pos[0]-(lo[0]+hi[0])/2)/length;
        if(!top&&cy<0&&opt.readable)u=-u;
        let v=top?-(pos[1]-(lo[1]+hi[1])/2)/length:-(pos[2]-(lo[2]+height*.46))/length;
        u-=opt.x/100;v-=opt.y/100;
        const su=(u*cs+v*sn)*length/span+.5,sv=(-u*sn+v*cs)*length/span*aspect+.5;
        if(su<0||su>1||sv<0||sv>1)continue;
        // Bilinear sampling in premultiplied alpha avoids dark transparent edges.
        const ix=su*(image.width-1),iy=sv*(image.height-1),x0=Math.floor(ix),y0=Math.floor(iy),fx=ix-x0,fy=iy-y0;
        const acc=[0,0,0,0];
        for(let dy=0;dy<2;dy++)for(let dx=0;dx<2;dx++){
          const at=(Math.min(image.height-1,y0+dy)*image.width+Math.min(image.width-1,x0+dx))*4;
          const w=(dx?fx:1-fx)*(dy?fy:1-fy),alpha=image.data[at+3]/255;
          acc[3]+=alpha*w;for(let k=0;k<3;k++)acc[k]+=image.data[at+k]*alpha*w;
        }
        const dst=(y*size+x)*4;
        if(acc[3]>0){for(let k=0;k<3;k++)out[dst+k]=acc[k]/acc[3];out[dst+3]=acc[3]*255*opt.opacity/100;}
      }
    }
    // One texel of alpha-aware bleed at UV edges, for the game's bilinear filter.
    const copy=out.slice();
    for(let y=1;y<size-1;y++)for(let x=1;x<size-1;x++){
      const p=(y*size+x)*4;if(copy[p+3])continue;
      for(const d of [-size,size,-1,1]){const q=p+d*4;if(copy[q+3]>200){out.set(copy.subarray(q,q+4),p);break;}}
    }
    return out;
  }
  const crcTable=Uint32Array.from({length:256},(_,n)=>{for(let k=0;k<8;k++)n=n&1?0xedb88320^(n>>>1):n>>>1;return n>>>0;});
  function crc(b){let c=0xffffffff;for(const v of b)c=crcTable[(c^v)&255]^(c>>>8);return(c^0xffffffff)>>>0;}
  function zip(files){
    const parts=[],central=[];let offset=0,cdSize=0;
    for(const {name,data} of files){
      const n=new TextEncoder().encode(name),c=crc(data),h=new Uint8Array(30+n.length),v=new DataView(h.buffer);
      v.setUint32(0,0x04034b50,true);v.setUint16(4,20,true);v.setUint16(6,0x800,true);v.setUint32(14,c,true);v.setUint32(18,data.length,true);v.setUint32(22,data.length,true);v.setUint16(26,n.length,true);h.set(n,30);
      const d=new Uint8Array(46+n.length),dv=new DataView(d.buffer);dv.setUint32(0,0x02014b50,true);dv.setUint16(4,20,true);dv.setUint16(6,20,true);dv.setUint16(8,0x800,true);dv.setUint32(16,c,true);dv.setUint32(20,data.length,true);dv.setUint32(24,data.length,true);dv.setUint16(28,n.length,true);dv.setUint32(42,offset,true);d.set(n,46);
      parts.push(h,data);central.push(d);offset+=h.length+data.length;cdSize+=d.length;
    }
    const end=new Uint8Array(22),v=new DataView(end.buffer);v.setUint32(0,0x06054b50,true);v.setUint16(8,files.length,true);v.setUint16(10,files.length,true);v.setUint32(12,cdSize,true);v.setUint32(16,offset,true);
    return new Blob([...parts,...central,end],{type:'application/zip'});
  }
  root.VinylCore={bake,zip,crc,cross};
})(typeof window==='undefined'?globalThis:window);
