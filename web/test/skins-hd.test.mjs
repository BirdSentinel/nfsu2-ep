import test from 'node:test';
import assert from 'node:assert/strict';
import { SkinSync } from '../src/net/skins.ts';
import { encodeSkinPng } from '../src/gpu/skin-png.ts';
test('HD upload waits for capability and falls back safely on an old server', async () => {
 const state=new SkinSync(), sent=[];state.send=m=>{sent.push(m);return true;};
 const hd=await encodeSkinPng(new Uint8Array(1024*1024*4));
 state.receive({t:'skin-ready'});assert.equal(state.maxSize,512);await state.publish(hd);assert.equal(sent.length,0);
 await state.publish(await encodeSkinPng(new Uint8Array(512*512*4)));assert.equal(sent.length,1);
 state.receive({t:'skin-ready',maxSize:1024});await state.publish(hd);assert.equal(sent.length,2);
 state.reset();assert.equal(state.maxSize,512);assert.equal(state.ready,false);
});
