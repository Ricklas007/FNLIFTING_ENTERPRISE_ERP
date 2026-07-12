const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('fnliftingDesktop', {
  retry: () => ipcRenderer.invoke('desktop:retry'),
  openLogs: () => ipcRenderer.invoke('desktop:openLogs'),
  close: () => ipcRenderer.invoke('desktop:close'),
  info: () => ipcRenderer.invoke('desktop:info'),
})
