const { contextBridge, ipcRenderer } = require('electron');

try {
  contextBridge.exposeInMainWorld('odin', {
    backendPort: () => process.env.BACKEND_PORT || '8765',
    selectDirectory: async () => ipcRenderer.invoke('select-directory'),
    getFontPath: () => ipcRenderer.invoke('get-font-path'),
    onBackendHealth: (cb) => ipcRenderer.on('backend-health', (_e, msg) => cb && cb(msg)),
    getBackendHealth: () => ipcRenderer.invoke('get-backend-health')
  });

  contextBridge.exposeInMainWorld('electronAPI', {
    openFileLocation: async (filePath) => ipcRenderer.invoke('open-file-location', filePath)
  });
} catch (e) {
  // noop: will be visible in devtools if needed
  console.error('Preload script error:', e);
}
