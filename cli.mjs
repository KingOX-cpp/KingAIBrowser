#!/usr/bin/env node
import { KingAI } from './client.mjs';
const args=process.argv.slice(2);
let mcpExecutable;
const offset=args.indexOf('--executable');
if(offset!==-1){mcpExecutable=args[offset+1];args.splice(offset,2);if(!mcpExecutable)throw new Error('--executable requires an absolute MCP path');}
const command=args[0]||'info';
if(args.length>1||!['info','tools','profiles'].includes(command)){
  process.stderr.write('Usage: kingai-browser [info|tools|profiles] [--executable PATH]\n');process.exitCode=2;
} else {
  const api=new KingAI({mcpExecutable});
  try {
    await api.connect();
    const result=command==='info'?{clientVersion:'0.3.0',mcp:api.serverInfo,api:await api.info()}:await api[command]();
    process.stdout.write(JSON.stringify(result,null,2)+'\n');
  } catch(error){process.stderr.write(JSON.stringify(error.details||{message:error.message})+'\n');process.exitCode=1;}
  finally{await api.close();}
}
