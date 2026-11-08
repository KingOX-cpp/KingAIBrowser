/** Periodic stderr feedback without mixing progress into JSON stdout. */
export function downloadProgress(enabled) {
  const started = performance.now();
  let bytes = 0, total, phase = 'Connecting', previousBytes = 0, previousTime = started, width = 0;
  const size = value => {
    for (const unit of ['B', 'KiB', 'MiB', 'GiB']) {
      if (value < 1024 || unit === 'GiB') return `${value.toFixed(1)} ${unit}`;
      value /= 1024;
    }
  };
  const render = (final = false) => {
    if (!enabled) return;
    const now = performance.now(), elapsed = (now - started) / 1000;
    const speed = final ? bytes / Math.max(elapsed, .001) : (bytes - previousBytes) / Math.max((now - previousTime) / 1000, .001);
    previousBytes = bytes; previousTime = now;
    const duration = seconds => `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${Math.floor(seconds % 60).toString().padStart(2, '0')}`;
    const amount = total > 0 ? `${size(bytes)} / ${size(total)} (${Math.min(100, bytes / total * 100).toFixed(1)}%)` : `${size(bytes)} / unknown total`;
    const eta = total > 0 && speed > 0 ? duration(Math.max(0, (total - bytes) / speed)) : '--';
    const line = `${phase}: ${amount} | ${size(speed)}/s | elapsed ${duration(elapsed)} | ETA ${eta}`;
    process.stderr.write((process.stderr.isTTY ? '\r' + line.padEnd(width) : line) + (final || !process.stderr.isTTY ? '\n' : ''));
    width = line.length;
  };
  render();
  const timer = enabled ? setInterval(render, process.stderr.isTTY ? 1000 : 5000) : undefined;
  timer?.unref();
  return {
    update(added = 0, length, stage) { bytes += added; if (length !== undefined) total = length; if (stage) phase = stage; },
    stop(success) { clearInterval(timer); phase = success ? 'Download complete' : 'Download stopped'; render(true); },
  };
}
