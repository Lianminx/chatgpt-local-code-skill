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
fs.writeFileSync(path.join(fixture,'safe.txt'),'harmless MCP verification fixture\n');
fs.writeFileSync(path.join(fixture,'.env'),'FAKE_SECRET=not-a-real-secret\n');
fs.writeFileSync(path.join(outside,'outside.txt'),'fake outside-root fixture\n');
fs.symlinkSync(path.join(outside,'outside.txt'),path.join(fixture,'escape.txt'));
const client=new Client({name:'chatgpt-local-code-check',version:'1.0.0'});
try{
  await client.connect(new StreamableHTTPClientTransport(endpoint));
  const tools=(await client.listTools()).tools;
  assert(tools.length>0 && tools.every(t=>t.annotations?.readOnlyHint===true));
  for(const name of ['write','edit','apply_patch','import_file','bash','handoff_to_agent','export_pro_context','codexpro_self_test'])assert(!tools.some(t=>t.name===name));
  const read=await client.callTool({name:'read',arguments:{path:`${relative}/safe.txt`}});
  assert(!read.isError && JSON.stringify(read).includes('harmless MCP verification fixture'));
  for(const target of [`${relative}/.env`,`${relative}/escape.txt`,path.join(outside,'outside.txt'),'../outside.txt']){
    assert((await client.callTool({name:'read',arguments:{path:target}})).isError,`Not blocked: ${target}`);
  }
  const write=await client.callTool({name:'write',arguments:{path:`${relative}/new.txt`,content:'must not be written'}}).catch(()=>({isError:true}));
  assert(write.isError);assert(!fs.existsSync(path.join(fixture,'new.txt')));
  assert.equal((await fetch(new URL('/mcp',base),{signal:AbortSignal.timeout(20000)})).status,401);
  assert.equal((await fetch(new URL('/admin/profile',base),{signal:AbortSignal.timeout(20000)})).status,404);
  console.log(JSON.stringify({passed:true,transport:base,tools:tools.map(t=>t.name),checks:['fake fixture read','all tools read-only','write rejected','sensitive path denied','root and symlink escape denied','unauthenticated 401','public management 404']},null,2));
}finally{
  await client.close().catch(()=>{});
  fs.rmSync(fixture,{recursive:true,force:true});fs.rmSync(outside,{recursive:true,force:true});
}
