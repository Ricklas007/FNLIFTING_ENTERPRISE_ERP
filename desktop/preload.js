const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('fnliftingDesktop', {
  retry: () => ipcRenderer.invoke('desktop:retry'),
  openLogs: () => ipcRenderer.invoke('desktop:openLogs'),
  close: () => ipcRenderer.invoke('desktop:close'),
  info: () => ipcRenderer.invoke('desktop:info'),
  getApiBaseUrl: async () => {
    const info = await ipcRenderer.invoke('desktop:info')
    return info.apiBaseUrl
  },
  onProgress: (callback) => {
    ipcRenderer.on('desktop:progress', (_event, message) => callback(message))
  },
})
