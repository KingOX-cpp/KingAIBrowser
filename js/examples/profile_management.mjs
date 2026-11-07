/** Saved environment CRUD without opening a browser.
 * Run: node js/examples/profile_management.mjs --live [--delete-created]
 * Requires a signed-in account and compatible installed MCP/Runtime.
 */
import { randomUUID } from 'node:crypto';
import { KingAI } from '../client.mjs';

async function manageProfiles(api, deleteCreated) {
  // Environment summaries do not contain full fingerprints or credentials.
  console.log('Saved environments:', await api.profiles());
  console.log('Capabilities:', await api.info());

  // A unique name avoids editing an existing identity by mistake.
  const name = `Node profile example ${randomUUID()}`;
  const { profileId } = await api.createProfile(name, { language: 'en-US' });
  console.log('Created ID:', profileId);
  console.log('Summary:', await api.profile(profileId));

  // Save settings while the profile is closed. patch recursively merges objects.
  // Save settings before startup; never log configurations or requests containing passwords.
  await api.updateProfile(profileId, {
    name: `${name} configured`,
    patch: { locale: { language: 'en-US', accept_languages: 'en-US,en' } },
  });
  console.log('Updated:', await api.profile(profileId));

  // Deletion is destructive; require a distinct explicit CLI flag.
  if (deleteCreated) {
    console.log('Deleted:', await api.deleteProfile(profileId, { confirm: true }));
  } else {
    console.log('Retained saved profile:', profileId);
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
