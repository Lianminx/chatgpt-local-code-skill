import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
const state=path.resolve(process.argv[2]);
const c=JSON.parse(fs.readFileSync(path.join(state,'settings.json'),'utf8'));
const token=fs.readFileSync(path.join(state,'mcp-token'),'utf8').trim();
const sdk=path.join(state,'runtime/node_modules/@modelcontextprotocol/sdk/dist/esm/client');
const {Client}=await import(pathToFileURL(path.join(sdk,'index.js')));
const {StreamableHTTPClientTransport}=await import(pathToFileURL(path.join(sdk,'streamableHttp.js')));
const base=process.argv.includes('--public')?`https://${c.domain}`:`http://127.0.0.1:${c.gatewayPort}`;
const endpoint=new URL('/mcp',base);endpoint.searchParams.set('codexpro_token',token);
const fixture=fs.mkdtempSync(path.join(c.root,'.mcp-readonly-check-'));
const outside=fs.mkdtempSync(path.join(os.tmpdir(),'mcp-outside-'));
const relative=path.relative(c.root,fixture).split(path.sep).join('/');
const client=new Client({name:'chatgpt-local-code-check',version:'1.0.0'});
try{
  const allowed='harmless MCP verification fixture';
  const excluded='excluded MCP verification fixture';
  fs.writeFileSync(path.join(fixture,'safe.txt'),allowed+'\n');
  fs.writeFileSync(path.join(fixture,'.env'),excluded+'\n');
  fs.writeFileSync(path.join(fixture,'CREDENTIALS.JSON'),excluded+'\n');
  fs.mkdirSync(path.join(fixture,'.ai-bridge'));
  fs.writeFileSync(path.join(fixture,'.ai-bridge','notes.txt'),excluded+'\n');
  fs.writeFileSync(path.join(outside,'outside.txt'),excluded+'\n');
  fs.symlinkSync(path.join(outside,'outside.txt'),path.join(fixture,'escape.txt'));
  await client.connect(new StreamableHTTPClientTransport(endpoint));
  const tools=(await client.listTools()).tools;
  assert.deepEqual(tools.map(t=>t.name).sort(),['read','search','tree']);
  assert(tools.every(t=>t.annotations?.readOnlyHint===true));
  const read=await client.callTool({name:'read',arguments:{path:`${relative}/safe.txt`}});
  assert(!read.isError && JSON.stringify(read).includes(allowed));
  for(const target of [`${relative}/.env`,`${relative}/CREDENTIALS.JSON`,`${relative}/.ai-bridge/notes.txt`,`${relative}/escape.txt`,path.join(outside,'outside.txt'),'../outside.txt']){
    assert((await client.callTool({name:'read',arguments:{path:target}})).isError,`Not blocked: ${target}`);
  }
  const tree=await client.callTool({name:'tree',arguments:{path:relative,include_hidden:true}});
  assert(!tree.isError && JSON.stringify(tree).includes('safe.txt'));
  assert(!/\.env|CREDENTIALS\.JSON|\.ai-bridge/.test(JSON.stringify(tree)));
  const search=await client.callTool({name:'search',arguments:{path:relative,query:'MCP verification fixture',include_hidden:true}});
  assert(!search.isError && JSON.stringify(search).includes(allowed) && !JSON.stringify(search).includes(excluded));
  const write=await client.callTool({name:'write',arguments:{path:`${relative}/new.txt`,content:'must not be written'}}).catch(()=>({isError:true}));
  assert(write.isError);assert(!fs.existsSync(path.join(fixture,'new.txt')));
  assert.equal((await fetch(new URL('/mcp',base),{signal:AbortSignal.timeout(20000)})).status,401);
  assert.equal((await fetch(new URL('/admin/profile',base),{signal:AbortSignal.timeout(20000)})).status,404);
  console.log(JSON.stringify({passed:true,transport:base,tools:tools.map(t=>t.name),checks:['exact tool allowlist','write rejected','fixture read, tree and search','sensitive path denied','root and symlink escape denied','unauthenticated 401','public management 404']},null,2));
}finally{
  await client.close().catch(()=>{});
  fs.rmSync(fixture,{recursive:true,force:true});fs.rmSync(outside,{recursive:true,force:true});
}
