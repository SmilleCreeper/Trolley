(() => {
  const clock = document.getElementById('home-clock');

  async function updateTime() {
    try {
      const runRes = await fetch('http://localhost:5050/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script: 'time.py' }),
        signal: AbortSignal.timeout(2000),
      });
      const { job_id } = await runRes.json();

      for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 50));
        const statusRes = await fetch(`http://localhost:5050/status/${job_id}`, { signal: AbortSignal.timeout(2000) });
        const status = await statusRes.json();
        if (status.done) {
          if (status.result) {
            const d = new Date(status.result.iso);
            clock.textContent = d.toLocaleTimeString('en-US', { hour12: false });
          }
          return;
        }
      }
      clock.textContent = 'ERR';
    } catch {
      clock.textContent = 'ERR';
    }
  }

  updateTime();
  setInterval(updateTime, 1000);

  document.getElementById('home-count').addEventListener('click', async () => {
    const result = document.getElementById('home-result');
    result.textContent = '';

    ProgressBar.show('Counting seconds from 2000...');

    try {
      const runRes = await fetch('http://localhost:5050/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script: 'seconds_since_2000.py' }),
        signal: AbortSignal.timeout(5000),
      });
      const { job_id } = await runRes.json();

      while (true) {
        const statusRes = await fetch(`http://localhost:5050/status/${job_id}`, { signal: AbortSignal.timeout(2000) });
        const status = await statusRes.json();

        if (status.done) {
          ProgressBar.set(100);
          if (status.result) {
            result.textContent = `Since 2000-01-01: ${status.result.seconds.toLocaleString()} seconds`;
          } else {
            result.textContent = `Error: ${status.error}`;
          }
          break;
        }

        ProgressBar.set(status.percent || 0, status.message || '');
        await new Promise(r => setTimeout(r, 150));
      }
    } catch {
      result.textContent = 'Failed to count';
    }

    setTimeout(() => ProgressBar.hide(), 500);
  });

  document.getElementById('home-crash').addEventListener('click', async () => {
    try {
      const res = await fetch('router/fallbacks.json');
      const fallbacks = await res.json();
      const entry = fallbacks[Math.floor(Math.random() * fallbacks.length)];
      showFallback(
        'Crash Fallback!',
        `Code in the: <b>${entry.module_debug}</b><br>Caused issue with the: <b>${entry.task_debug}</b><br>Because of the: <b>${entry.cause_debug}</b>`
      );
    } catch {
      showFallback('Crash Fallback!', 'Simulated crash — reason unknown.');
    }
  });
})();
