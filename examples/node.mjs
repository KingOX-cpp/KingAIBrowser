import { pathToFileURL } from 'node:url';

export async function runSample(api, name='Node SDK 演示') {
  const info=await api.info();
  const profiles=await api.profiles();
  const profile=await api.createProfile(name);
  const browser=await api.start({profile_id:profile.profileId});
  await browser.newTab('https://example.com');
  const page=await browser.read();
  const preview=await browser.evaluatePreview('({title:document.title,text:document.body.innerText})');
  await browser.detach();
  return {info,profiles,profileId:profile.profileId,page,preview};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  if(!process.argv.includes('--live'))throw new Error('Pass --live to create an environment in your real KingAI installation');
  const {KingAI}=await import('../client.mjs');
  const api=new KingAI();
  try {console.log(await runSample(api));}finally{await api.close();}
}
