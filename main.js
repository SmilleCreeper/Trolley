const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const http = require('http');
const fs = require('fs');

const PYTHON_PORT = 5050;
const MY_PORT = 5051;
const HEARTBEAT_INTERVAL = 1000;
const REQUEST_TIMEOUT = 2000;

let win;

function startHeartbeatServer() {
  const server = http.createServer((req, res) => {
    if (req.url === '/heartbeat') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ok' }));
    } else {
      res.writeHead(404);
      res.end();
    }
  });
  server.listen(MY_PORT, 'localhost');
  return server;
}

function checkPython() {
  let misses = 0;
  setTimeout(() => {
    const check = setInterval(() => {
      const req = http.get(`http://localhost:${PYTHON_PORT}/heartbeat`, { timeout: REQUEST_TIMEOUT }, (res) => {
        res.resume();
        misses = 0;
      });
      req.on('error', () => {
        misses++;
        if (misses >= 3) {
          console.log('[electron] Python heartbeat failed, shutting down');
          clearInterval(check);
          app.quit();
        }
      });
      req.setTimeout(REQUEST_TIMEOUT, () => {
        req.destroy();
      });
    }, HEARTBEAT_INTERVAL);
  }, 3000);
}

ipcMain.handle('fs-readdir', (_, relPath) => {
  const full = path.join(__dirname, relPath);
  return fs.readdirSync(full, { withFileTypes: true }).map(e => ({
    name: e.name,
    isDirectory: e.isDirectory(),
  }));
});

ipcMain.handle('fs-readfile', (_, relPath, encoding) => {
  const full = path.join(__dirname, relPath);
  if (encoding === 'base64') {
    const data = fs.readFileSync(full);
    const ext = path.extname(relPath).slice(1);
    return `data:image/${ext};base64,${data.toString('base64')}`;
  }
  return fs.readFileSync(full, 'utf-8');
});

ipcMain.handle('fs-writefile', (_, relPath, content) => {
  const full = path.join(__dirname, relPath);
  fs.writeFileSync(full, content, 'utf-8');
});

app.whenReady().then(() => {
  startHeartbeatServer();
  checkPython();

  win = new BrowserWindow({
    width: 1200,
    height: 800,
    frame: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  ipcMain.on('win-close', () => win.close());
  ipcMain.on('win-minimize', () => win.minimize());
  ipcMain.on('win-maximize', () => {
    if (win.isMaximized()) win.unmaximize();
    else win.maximize();
  });

  win.loadFile('index.html');
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
