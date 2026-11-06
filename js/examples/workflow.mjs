import { randomUUID } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { KingAI } from '../client.mjs';

const url = 'http://127.0.0.1:8765/demo.html';

async function oneRef(browser, selector) {
  const result = await browser.query({ selector, include_html: true, limit: 2 });
  console.log('DOM query:', result);
  if (result.elements?.length !== 1 || !result.elements[0].ref) {
    throw new Error(`Expected exactly one actionable DOM element: ${selector}`);
  }
  return result.elements[0].ref;
}

export async function runWorkflow(api) {
  console.log('Capabilities:', await api.info());
  console.log('Saved environments:', await api.profiles());
  const name = `Node workflow ${randomUUID()}`;
  const { profileId } = await api.createProfile(name, { language: 'en-US' });
  // Save profile settings before starting; never change someone else's identity.
  await api.updateProfile(profileId, { name: `${name} configured` });
  console.log('Configured environment:', await api.profile(profileId));
  const browser = await api.start({ profile_id: profileId });
  try {
    await browser.newTab(url);
    await browser.wait({ selector: '#demo-form', state: 'visible', timeout_ms: 15000 });
    console.log('Interactive DOM:', await browser.snapshot({ mode: 'interactive', limit: 30 }));
    console.log('DOM inventory:', await browser.query({ limit: 30, include_html: true, max_chars: 12000 }));
    // Obtain fresh server refs before acting. humanize:false makes this demo
    // independent of humanize entitlement; use true when you have that entitlement.
    await browser.fill(undefined, 'KingAI Node', { ref: await oneRef(browser, '#name'), humanize: false });
    await browser.fill(undefined, 'Hello from the Node SDK', { ref: await oneRef(browser, '#message'), humanize: false });
    await browser.click(undefined, { ref: await oneRef(browser, '#submit'), humanize: false });
    await browser.wait({ selector: '#result[data-submitted="true"]', text: 'Submitted: KingAI Node', timeout_ms: 10000 });
    const result = await browser.evaluate("document.querySelector('#result').textContent");
    if (result !== 'Submitted: KingAI Node | Hello from the Node SDK') throw new Error(`Unexpected form result: ${result}`);
    console.log('Submission result:', result);
    console.log('Page:', await browser.read());
    console.log('Tabs:', await browser.tabs());
    return { profileId, result };
  } finally { await browser.detach(); }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  if (!process.argv.includes('--live')) throw new Error('Pass --live to create and operate a real saved environment');
  const api = new KingAI();
  try { console.log(await runWorkflow(api)); } finally { await api.close(); }
}
