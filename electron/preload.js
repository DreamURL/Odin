import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('odin', {
  backendPort: () => process.env.BACKEND_PORT || '8765',
  selectDirectory: async () => ipcRenderer.invoke('select-directory')
});

contextBridge.exposeInMainWorld('electronAPI', {
  openFileLocation: async (filePath) => ipcRenderer.invoke('open-file-location', filePath)
});
