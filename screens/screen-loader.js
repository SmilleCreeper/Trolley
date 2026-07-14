let routerConfig = { default_screen: 'home', fallback_return: 'home' };

async function loadRouterConfig() {
  try {
    const res = await fetch('router/defaults.json');
    routerConfig = await res.json();
  } catch (_) {}
}

async function loadDefaultScreen() {
  await loadRouterConfig();
  loadScreen(routerConfig.default_screen);
}

function loadScreen(name) {
  const container = document.getElementById('screen-container');
  const base = `screens/${name}`;

  document.querySelectorAll('script[data-screen]').forEach(s => s.remove());

  fetch(`${base}/index.html`)
    .then(r => r.text())
    .then(html => {
      container.innerHTML = html;

      const linkId = `screen-css-${name}`;
      if (!document.getElementById(linkId)) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = `${base}/style.css`;
        link.id = linkId;
        document.head.appendChild(link);
      }

      const script = document.createElement('script');
      script.src = `${base}/script.js?v=${Date.now()}`;
      script.dataset.screen = name;
      document.body.appendChild(script);
    });
}

function navigateTo(name) {
  loadScreen(name);
}

function showFallback(cause, description) {
  window.__fallbackData = { cause, description, returnTo: routerConfig.fallback_return };
  navigateTo('fallback');
}
