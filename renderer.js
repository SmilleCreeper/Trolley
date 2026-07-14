document.getElementById('btn-minimize').onclick = () => window.electronAPI.minimize();
document.getElementById('btn-close').onclick = () => window.electronAPI.close();

ProgressBar.init();

loadDefaultScreen();
