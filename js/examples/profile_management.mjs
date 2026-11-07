/** Saved environment CRUD without opening a browser.
 * 中文：环境列表、创建、读取、配置与显式删除；不会修改已有环境。
 * Run: node js/examples/profile_management.mjs --live [--delete-created]
 * Requires a signed-in account and compatible installed MCP/Runtime.
 */
import { randomUUID } from 'node:crypto';
import { KingAI } from '../client.mjs';

async function manageProfiles(api, deleteCreated) {
  // Environment summaries do not contain full fingerprints or credentials.
  console.log('Saved environments / 已保存环境:', await api.profiles());
  console.log('Capabilities / 能力:', await api.info());

  // A unique name avoids editing an existing identity by mistake.
  const name = `Node profile example ${randomUUID()}`;
  const { profileId } = await api.createProfile(name, { language: 'en-US' });
  console.log('Created / 新环境 ID:', profileId);
  console.log('Summary / 摘要:', await api.profile(profileId));

  // Save settings while the profile is closed. patch recursively merges objects.
  // 在启动前保存；不输出带密码的配置或请求内容。
  await api.updateProfile(profileId, {
    name: `${name} configured`,
    patch: { locale: { language: 'en-US', accept_languages: 'en-US,en' } },
  });
  console.log('Updated / 修改后摘要:', await api.profile(profileId));

  // Deletion is destructive; require a distinct explicit CLI flag.
  if (deleteCreated) {
    console.log('Deleted / 删除:', await api.deleteProfile(profileId, { confirm: true }));
  } else {
    console.log('Retained saved profile / 已保留环境:', profileId);
  }
}

if (!process.argv.includes('--live')) {
  throw new Error('Pass --live to create/configure a real saved environment');
}
const api = new KingAI();
try {
  await manageProfiles(api, process.argv.includes('--delete-created'));
} finally {
  // Closing the client disconnects its MCP; no browser was started here.
  await api.close();
}
