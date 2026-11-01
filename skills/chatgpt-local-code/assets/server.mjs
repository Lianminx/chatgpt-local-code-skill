import fs from 'node:fs';
import http from 'node:http';
import {spawn} from 'node:child_process';
import path from 'node:path';
const state=path.resolve(process.argv[2]);
const c=JSON.parse(fs.readFileSync(path.join(state,'settings.json'),'utf8'));
const token=fs.readFileSync(path.join(state,'mcp-token'),'utf8').trim();
const child=spawn(process.execPath,['dist/http.js'],{
  cwd:path.join(state,'runtime'),
  env:{PATH:process.env.PATH,HOME:process.env.HOME,
    CODEXPRO_HOME:path.join(state,'profile'),CODEXPRO_ROOT:c.root,CODEXPRO_ALLOWED_ROOTS:c.root,
    CODEXPRO_HOST:'127.0.0.1',CODEXPRO_PORT:String(c.port),CODEXPRO_HTTP_TOKEN:token,
    CODEXPRO_REQUIRE_HTTP_TOKEN:'1',CODEXPRO_BASH_MODE:'off',CODEXPRO_WRITE_MODE:'off',
    CODEXPRO_CODEX_SESSIONS:'off',CODEXPRO_TOOL_MODE:'standard',CODEXPRO_CONNECTION_TEST:'1',
    CODEXPRO_BLOCKED_GLOBS:'**/auth.json,**/credentials.json,**/.npmrc,**/.pypirc,**/.netrc,**/.aws/**,**/.azure/**,**/.config/gcloud/**,**/*.p12,**/*.pfx,**/*.keystore'},
  stdio:['ignore','inherit','inherit']
});
// Keep administrative routes off the public listener; authentication stays upstream.
const gateway=http.createServer((req,res)=>{
  let url;try{url=new URL(req.url,'http://localhost');}catch{res.writeHead(400).end();return;}
  if(url.pathname!=='/mcp'){res.writeHead(404).end();return;}
  const out=http.request({hostname:'127.0.0.1',port:c.port,path:req.url,method:req.method,headers:req.headers},reply=>{
    res.writeHead(reply.statusCode,reply.headers);reply.pipe(res);
  });
  out.on('error',()=>{if(!res.headersSent)res.writeHead(502);res.end();});
  res.on('close',()=>out.destroy());req.pipe(out);
});
let stopping=false;
function stop(code=0){
  if(stopping)return;stopping=true;child.kill('SIGTERM');gateway.close();
  setTimeout(()=>{child.kill('SIGKILL');process.exit(code);},1500).unref();
}
child.on('error',e=>{console.error(e.message);stop(1);});
child.on('exit',code=>{if(!stopping){gateway.close();process.exit(code||1);}});
gateway.on('error',e=>{console.error(e.message);stop(1);});
process.on('SIGTERM',()=>stop());process.on('SIGINT',()=>stop());
gateway.listen(c.gatewayPort,'127.0.0.1');
