const { app, BrowserWindow, ipcMain, shell } = require('electron')
const fs = require('fs')
const http = require('http')
const path = require('path')
const { BackendManager } = require('./runtime/backend')
const { migrateLegacyDatabase } = require('./runtime/legacyMigration')
const { LogManager } = require('./runtime/logs')
const { choosePort } = require('./runtime/ports')
const { createRuntimePaths, frontendDistDir, rootDir } = require('./runtime/paths')

const APP_NAME = 'FNLIFTING ENTERPRISE ERP'
const MIN_SPLASH_MS = 2500

let runtimePaths = null
let logManager = null
let backendManager = null
let staticServer = null
let splashWindow = null
let mainWindow = null
let errorWindow = null
let lastStartupError = null
let startupInProgress = false
let backendPort = null
let frontendPort = null

const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  app.quit()
}

function progress(message) {
  if (logManager) logManager.write('startup', message)
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.webContents.send('desktop:progress', message)
  }
}

function httpGet(url, timeoutMs = 2500) {
  return new Promise((resolve, reject) => {
    const request = http.get(url, { timeout: timeoutMs }, (response) => {
      const chunks = []
      response.on('data', (chunk) => chunks.push(chunk))
      response.on('end', () => {
        if (response.statusCode && response.statusCode >= 200 && response.statusCode < 300) {
          resolve(Buffer.concat(chunks).toString('utf8'))
        } else {
          reject(new Error(`HTTP ${response.statusCode}`))
        }
      })
    })
    request.on('timeout', () => request.destroy(new Error('timeout')))
    request.on('error', reject)
  })
}

async function waitForBackend(timeoutMs = 120000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      await httpGet(`http://127.0.0.1:${backendPort}/ready`)
      return
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 750))
    }
  }
  throw new Error('O backend local não ficou pronto dentro do tempo esperado.')
}

function contentType(filePath) {
  const ext = path.extname(filePath).toLowerCase()
  return {
    '.html': 'text/html; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.ico': 'image/x-icon',
    '.svg': 'image/svg+xml',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
  }[ext] || 'application/octet-stream'
}

function proxyToBackend(request, response) {
  const proxyRequest = http.request({
    hostname: '127.0.0.1',
    port: backendPort,
    method: request.method,
    path: request.url,
    headers: {
      ...request.headers,
      host: `127.0.0.1:${backendPort}`,
      origin: `http://127.0.0.1:${frontendPort}`,
    },
  }, (proxyResponse) => {
    response.writeHead(proxyResponse.statusCode || 502, proxyResponse.headers)
    proxyResponse.pipe(response)
  })
  proxyRequest.on('error', (error) => {
    response.writeHead(502, { 'Content-Type': 'application/json' })
    response.end(JSON.stringify({ detail: `Backend indisponível: ${error.message}` }))
  })
  request.pipe(proxyRequest)
}

function startFrontendServer() {
  if (staticServer) return Promise.resolve()
  const dist = frontendDistDir(app)
  if (!fs.existsSync(path.join(dist, 'index.html'))) {
    throw new Error(`Frontend de produção não encontrado em ${dist}. Execute npm run build antes de abrir o app desktop.`)
  }
  staticServer = http.createServer((request, response) => {
    const reqUrl = new URL(request.url || '/', `http://127.0.0.1:${frontendPort}`)
    if (reqUrl.pathname.startsWith('/api/') || reqUrl.pathname === '/ready' || reqUrl.pathname === '/health') {
      proxyToBackend(request, response)
      return
    }
    const decoded = decodeURIComponent(reqUrl.pathname)
    const safePath = path.normalize(decoded).replace(/^(\.\.[/\\])+/, '')
    let filePath = path.join(dist, safePath === '/' ? 'index.html' : safePath)
    const resolvedDist = path.resolve(dist)
    const resolvedFile = path.resolve(filePath)
    if (!resolvedFile.startsWith(resolvedDist) || !fs.existsSync(resolvedFile) || fs.statSync(resolvedFile).isDirectory()) {
      filePath = path.join(dist, 'index.html')
    }
    response.writeHead(200, {
      'Content-Type': contentType(filePath),
      'Cache-Control': filePath.endsWith('index.html') ? 'no-cache' : 'public, max-age=31536000, immutable',
      'Content-Security-Policy': `default-src 'self'; connect-src 'self' http://127.0.0.1:${frontendPort} http://127.0.0.1:${backendPort}; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; object-src 'none'; frame-ancestors 'none'`,
    })
    fs.createReadStream(filePath).pipe(response)
  })
  return new Promise((resolve, reject) => {
    staticServer.once('error', reject)
    staticServer.listen(frontendPort, '127.0.0.1', () => {
      logManager.write('desktop', `frontend server ready on ${frontendPort}`)
      resolve()
    })
  })
}

function hardenWindow(window) {
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://127.0.0.1') || url.startsWith('http://localhost')) return { action: 'deny' }
    shell.openExternal(url)
    return { action: 'deny' }
  })
  window.webContents.on('will-navigate', (event, url) => {
    const allowed = `http://127.0.0.1:${frontendPort}`
    if (!url.startsWith(allowed)) {
      event.preventDefault()
      shell.openExternal(url).catch(() => undefined)
    }
  })
}

function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 760,
    height: 460,
    frame: false,
    resizable: false,
    show: true,
    backgroundColor: '#020817',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })
  splashWindow.loadFile(path.join(__dirname, 'splash.html'))
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1120,
    minHeight: 740,
    show: false,
    title: APP_NAME,
    backgroundColor: '#020817',
    icon: path.join(__dirname, 'assets', process.platform === 'win32' ? 'icon.ico' : 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })
  mainWindow.removeMenu()
  hardenWindow(mainWindow)
  mainWindow.loadURL(`http://127.0.0.1:${frontendPort}`)
  mainWindow.once('ready-to-show', () => {
    if (splashWindow && !splashWindow.isDestroyed()) splashWindow.close()
    mainWindow.show()
    logManager.write('startup', 'DESKTOP_READY')
    if (process.env.FNLIFTING_DESKTOP_SMOKE_TEST === '1') {
      setTimeout(() => app.quit(), Number(process.env.FNLIFTING_DESKTOP_SMOKE_CLOSE_MS || 3500))
    }
  })
}

function createErrorWindow(error) {
  lastStartupError = error
  if (splashWindow && !splashWindow.isDestroyed()) splashWindow.close()
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.close()
  errorWindow = new BrowserWindow({
    width: 760,
    height: 520,
    resizable: false,
    title: `${APP_NAME} - Erro`,
    backgroundColor: '#020817',
    icon: path.join(__dirname, 'assets', process.platform === 'win32' ? 'icon.ico' : 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })
  errorWindow.removeMenu()
  hardenWindow(errorWindow)
  errorWindow.loadFile(path.join(__dirname, 'error.html'))
}

async function prepareRuntime() {
  runtimePaths = createRuntimePaths(app)
  logManager = new LogManager(runtimePaths)
  logManager.write('startup', `boot root=${rootDir(app)} userData=${runtimePaths.base}`)
  backendPort = await choosePort(process.env.FNLIFTING_BACKEND_PORT || 18200, 18200, 18350)
  frontendPort = await choosePort(process.env.FNLIFTING_FRONTEND_PORT || 18280, 18280, 18450)
  backendManager = new BackendManager({ app, paths: runtimePaths, logManager, backendPort, frontendPort })
}

async function bootApplication() {
  if (startupInProgress) return
  startupInProgress = true
  try {
    const startedAt = Date.now()
    await prepareRuntime()
    createSplashWindow()
    progress('Preparando armazenamento local')
    migrateLegacyDatabase({ app, runtimePaths, rootDir: rootDir(app), logManager })
    progress('Validando configuração segura')
    progress('Migrando base de dados')
    await backendManager.migrateAndSeed()
    progress('Iniciando serviços locais')
    backendManager.startServe()
    progress('Validando backend')
    await waitForBackend()
    progress('Carregando interface')
    await startFrontendServer()
    const elapsed = Date.now() - startedAt
    if (elapsed < MIN_SPLASH_MS) {
      await new Promise((resolve) => setTimeout(resolve, MIN_SPLASH_MS - elapsed))
    }
    createMainWindow()
    logManager.write('desktop', 'boot success')
  } catch (error) {
    if (logManager) logManager.write('desktop', `boot failed: ${error.stack || error.message}`)
    createErrorWindow(error)
  } finally {
    startupInProgress = false
  }
}

function stopChildren() {
  if (staticServer) {
    staticServer.close()
    staticServer = null
  }
  if (backendManager) backendManager.stop()
}

ipcMain.handle('desktop:retry', async () => {
  if (errorWindow && !errorWindow.isDestroyed()) errorWindow.close()
  stopChildren()
  await bootApplication()
  return true
})

ipcMain.handle('desktop:openLogs', async () => {
  if (!runtimePaths) runtimePaths = createRuntimePaths(app)
  await shell.openPath(runtimePaths.logs)
  return true
})

ipcMain.handle('desktop:close', () => {
  app.quit()
})

ipcMain.handle('desktop:info', () => ({
  appName: APP_NAME,
  version: app.getVersion(),
  backendPort,
  frontendPort,
  apiBaseUrl: frontendPort ? `http://127.0.0.1:${frontendPort}/api/v1` : '/api/v1',
  error: lastStartupError ? String(lastStartupError.message || lastStartupError) : null,
  logDir: runtimePaths ? runtimePaths.logs : null,
  dataDir: runtimePaths ? runtimePaths.data : null,
}))

app.on('second-instance', () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.focus()
  } else if (errorWindow) {
    errorWindow.focus()
  }
})
app.whenReady().then(bootApplication)
app.on('before-quit', stopChildren)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) bootApplication()
})
process.on('uncaughtException', (error) => {
  if (logManager) logManager.write('desktop', `uncaughtException: ${error.stack || error.message}`)
})
