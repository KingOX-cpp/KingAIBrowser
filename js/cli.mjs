#!/usr/bin/env node
import { KingAI } from './client.mjs';
const args=process.argv.slice(2);
let mcpExecutable;
const offset=args.indexOf('--executable');
if(offset!==-1){mcpExecutable=args[offset+1];args.splice(offset,2);if(!mcpExecutable)throw new Error('--executable requires an absolute MCP path');}
const command=args[0]||'info';
if(args.length>1||!['info','tools','profiles','doctor'].includes(command)){
  process.stderr.write('Usage: kingai-browser [info|tools|profiles|doctor] [--executable PATH]\n');process.exitCode=2;
} else if(command==='doctor') {
  const {doctor}=await import('./doctor.mjs');
  const report=await doctor(mcpExecutable);
  process.stdout.write(JSON.stringify(report,null,2)+'\n');
  process.exitCode=report.status==='error'?1:0;
} else {
  const api=new KingAI({mcpExecutable});
  try {
    await api.connect();
    let result;
    if(command==='info') {
      const names=new Set((await api.tools()).map(tool=>tool.name));
      result={clientVersion:'0.3.0',mcp:api.serverInfo,
        api:names.has('sdk_info')?await api.info():null,
        compatibilityNote:names.has('sdk_info')?null:'Older MCP: sdk_info is unavailable; inspect tools for supported capabilities'};
    } else result=await api[command]();
    process.stdout.write(JSON.stringify(result,null,2)+'\n');
  } catch(error){process.stderr.write(JSON.stringify(error.details||{message:error.message})+'\n');process.exitCode=1;}
  finally{await api.close();}
}
