const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  close: () => ipcRenderer.send('win-close'),
  minimize: () => ipcRenderer.send('win-minimize'),
  maximize: () => ipcRenderer.send('win-maximize'),
  fsReaddir: (relPath) => ipcRenderer.invoke('fs-readdir', relPath),
  fsReadfile: (relPath, encoding) => ipcRenderer.invoke('fs-readfile', relPath, encoding),
  fsWritefile: (relPath, content) => ipcRenderer.invoke('fs-writefile', relPath, content),
});
