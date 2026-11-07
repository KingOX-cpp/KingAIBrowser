import { createWriteStream } from 'node:fs';
import { mkdir, mkdtemp, rename, rm, open } from 'node:fs/promises';
import { join, isAbsolute } from 'node:path';
import { homedir, machine } from 'node:os';
import { createHash } from 'node:crypto';
import { spawn, execFileSync } from 'node:child_process';
import { Readable, Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { childEnvironment, KingAIError } from './discovery.mjs';

function target() {
  if (process.platform === 'win32') {
    const native = (process.env.PROCESSOR_ARCHITEW6432 ?? process.env.PROCESSOR_ARCHITECTURE ?? machine()).toLowerCase();
    if (!['amd64', 'x86_64'].includes(native)) throw new Error('Windows installer requires Intel/AMD x64; ARM and 32-bit Windows are unsupported');
    return ['windows-x64', 'KingAIBrowserSetup.exe'];
  }
  if (process.platform === 'darwin') {
    if (!['arm64', 'aarch64'].includes(machine().toLowerCase()) && execFileSync('/usr/sbin/sysctl', ['-in', 'hw.optional.arm64'], { encoding: 'utf8' }).trim() !== '1') {
      throw new Error('macOS installer requires Apple Silicon');
    }
    return ['macos-arm64', 'KingAIBrowser.dmg'];
  }
  throw new Error('Installers support Windows x64 and Apple Silicon macOS only');
}

/** Download the official installer; optionally open its UI without claiming completion. */
export async function install({ downloadDir, downloadOnly = false, sha256 } = {}) {
  const [platform, filename] = target();
  if (sha256 !== undefined && !/^[a-f\d]{64}$/i.test(sha256)) throw new TypeError('sha256 must be 64 hexadecimal characters');
  const directory = downloadDir ?? (process.platform === 'win32' ? 'D:\\code\\KingAIBrowser-downloads' : join(homedir(), 'Downloads', 'KingAIBrowser'));
  if (!isAbsolute(directory)) throw new TypeError('downloadDir must be absolute');
  await mkdir(directory, { recursive: true });
  const work = await mkdtemp(join(directory, 'download-'));
  const partial = join(work, `${filename}.part`), installerPath = join(work, filename);
  const url = `https://161.118.255.111/download/${filename}`;
  const digest = createHash('sha256');
  let bytes = 0, actual;
  const signal = AbortSignal.timeout(600000);
  try {
    // Manual redirects prevent downgrade to HTTP before any insecure request is sent.
    let current = url, response;
    for (let redirects = 0; redirects <= 5; redirects++) {
      response = await fetch(current, { redirect: 'manual', signal });
      if (![301,302,303,307,308].includes(response.status)) break;
      const location = response.headers.get('location');
      await response.body?.cancel();
      if (!location || redirects === 5) throw new Error('Invalid or excessive installer redirects');
      current = new URL(location, current).href;
      if (new URL(current).protocol !== 'https:') throw new Error('Installer redirects must use HTTPS');
    }
    if (response.status !== 200 || !response.body || response.headers.get('content-type')?.includes('text/html')) throw new Error('Server did not return an installer file');
    const declared = response.headers.get('content-length');
    const counter = new Transform({ transform(chunk, encoding, callback) {
      bytes += chunk.length;
      if (bytes > 3 * 1024 ** 3) return callback(new Error('Installer exceeds 3 GiB'));
      digest.update(chunk); callback(null, chunk);
    } });
    await pipeline(Readable.fromWeb(response.body), counter, createWriteStream(partial, { flags: 'wx' }), { signal });
    if (!bytes || (declared !== null && Number(declared) !== bytes)) throw new Error('Installer download is incomplete');
    actual = digest.digest('hex');
    if (sha256 && actual !== sha256.toLowerCase()) throw new Error('Installer SHA-256 mismatch');
    if (platform === 'windows-x64') {
      const file = await open(partial, 'r');
      try { const header = Buffer.alloc(2); await file.read(header, 0, 2, 0); if (header.toString() !== 'MZ') throw new Error('Invalid Windows executable'); }
      finally { await file.close(); }
    }
    await rename(partial, installerPath);
  } catch (error) {
    throw new KingAIError({ code: 'INSTALL_DOWNLOAD_FAILED', message: error.message, hint: 'Check network access and TLS certificate validity; certificate verification is never disabled' });
  } finally { await rm(partial, { force: true }); }
  const result = { status: 'downloaded', platform, installerPath, sha256: actual, checksumVerified: sha256 !== undefined, bytes, url };
  if (!downloadOnly) {
    const command = process.platform === 'win32' ? installerPath : '/usr/bin/open';
    const args = process.platform === 'win32' ? [] : [installerPath];
    await new Promise((resolve, reject) => {
      const child = spawn(command, args, { detached: true, stdio: 'ignore', env: childEnvironment({}) });
      child.once('error', reject); child.once('spawn', () => { child.unref(); resolve(); });
    });
    result.status = 'installer_started';
    result.nextStep = 'Complete the native installer/DMG installation, open Manager and sign in, then run doctor. Installation has not been verified.';
  }
  return result;
}
