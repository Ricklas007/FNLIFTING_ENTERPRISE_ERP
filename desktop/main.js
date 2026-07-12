const { app, BrowserWindow, ipcMain, shell } = require('electron')
const crypto = require('crypto')
const fs = require('fs')
const http = require('http')
const path = require('path')
const { spawn } = require('child_process')

const APP_NAME = 'FNLIFTING ENTERPRISE ERP'
const BACKEND_PORT = Number(process.env.FNLIFTING_BACKEND_PORT || 18200)
const FRONTEND_PORT = Number(process.env.FNLIFTING_FRONTEND_PORT || 18280)
const MIN_SPLASH_MS = 2500

let backendProcess = null
let staticServer = null
let splashWindow = null
let mainWindow = null
let errorWindow = null
let lastStartupError = null
let startupInProgress = false
let logDir = null
let backendLogFile = null
let electronLogFile = null

function rootDir() {
  return app.isPackaged ? process.resourcesPath : path.resolve(__dirname, '..')
}

function frontendDistDir() {
  return path.join(rootDir(), 'frontend', 'dist')
}

function backendDir() {
  return path.join(rootDir(), 'backend')
}

function userDataDir() {
  return app.getPath('userData')
}

function ensureRuntimeDirs() {
  const base = userDataDir()
  logDir = path.join(base, 'logs')
  backendLogFile = path.join(logDir, 'backend.log')
  electronLogFile = path.join(logDir, 'electron.log')
  for (const dir of [base, logDir, path.join(base, 'data'), path.join(base, 'secrets')]) {
    fs.mkdirSync(dir, { recursive: true })
  }
}

function appendElectronLog(message) {
  if (!electronLogFile) return
  fs.appendFileSync(electronLogFile, `[${new Date().toISOString()}] ${message}\n`, 'utf8')
}

function readOrCreateSecret(name) {
  const file = path.join(userDataDir(), 'secrets', name)
  if (fs.existsSync(file)) return fs.readFileSync(file, 'utf8').trim()
  const value = crypto.randomBytes(48).toString('hex')
  fs.writeFileSync(file, value, { encoding: 'utf8', mode: 0o600 })
  return value
}

function backendEnvironment() {
  const dataDir = path.join(userDataDir(), 'data')
  return {
    ...process.env,
    APP_NAME,
    APP_VERSION: app.getVersion(),
    ENVIRONMENT: 'desktop',
    DEBUG: 'false',
    AUTO_CREATE_SCHEMA: 'true',
    SECURITY_HEADERS_ENABLED: 'true',
    DATABASE_URL: `sqlite:///${path.join(dataDir, 'fnlifting.db').replace(/\\/g, '/')}`,
    SECRET_KEY: readOrCreateSecret('secret.key'),
    BACKUP_ENCRYPTION_KEY: readOrCreateSecret('backup.key'),
    CORS_ORIGINS: `http://127.0.0.1:${FRONTEND_PORT},http://localhost:${FRONTEND_PORT}`,
    ALLOWED_HOSTS: `127.0.0.1,localhost`,
  }
}

function pythonCandidates() {
  const backend = backendDir()
  const explicit = process.env.FNLIFTING_PYTHON ? [{ command: process.env.FNLIFTING_PYTHON, prefix: [] }] : []
  return [
    ...explicit,
    { command: path.join(backend, '.venv', 'Scripts', 'python.exe'), prefix: [] },
    { command: path.join(backend, '.venv', 'bin', 'python'), prefix: [] },
    { command: 'python', prefix: [] },
    { command: 'py', prefix: ['-3'] },
  ]
}

function spawnLogged(command, args, options = {}) {
  const out = fs.openSync(backendLogFile, 'a')
  const err = fs.openSync(backendLogFile, 'a')
  return spawn(command, args, {
    cwd: backendDir(),
    env: backendEnvironment(),
    windowsHide: true,
    stdio: ['ignore', out, err],
    ...options,
  })
}

function runCommand(command, args, timeoutMs = 90000) {
  return new Promise((resolve, reject) => {
    appendElectronLog(`run: ${command} ${args.join(' ')}`)
    const child = spawnLogged(command, args)
    let settled = false
    const timer = setTimeout(() => {
      if (settled) return
      settled = true
      child.kill()
      reject(new Error(`Tempo esgotado ao executar ${command} ${args.join(' ')}`))
    }, timeoutMs)
    child.on('error', (error) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      reject(error)
    })
    child.on('exit', (code) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      code === 0 ? resolve() : reject(new Error(`Comando falhou com código ${code}: ${command} ${args.join(' ')}`))
    })
  })
}

async function findPython() {
  for (const candidate of pythonCandidates()) {
    try {
      if (candidate.command.includes(path.sep) && !fs.existsSync(candidate.command)) continue
      await runCommand(candidate.command, [...candidate.prefix, '-c', 'import fastapi, uvicorn, sqlalchemy; print("backend-runtime-ok")'], 25000)
      appendElectronLog(`python selected: ${candidate.command}`)
      return candidate
    } catch (error) {
      appendElectronLog(`python candidate failed: ${candidate.command}: ${error.message}`)
    }
  }
  throw new Error('Backend Python não encontrado ou dependências FastAPI/Uvicorn ausentes. Instale as dependências do backend ou defina FNLIFTING_PYTHON.')
}

function httpGetJson(url, timeoutMs = 2500) {
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

async function waitForBackend(timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      await httpGetJson(`http://127.0.0.1:${BACKEND_PORT}/ready`)
      return true
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 750))
    }
  }
  throw new Error('O backend local não ficou pronto dentro do tempo esperado.')
}

async function startBackend() {
  try {
    await httpGetJson(`http://127.0.0.1:${BACKEND_PORT}/ready`, 1000)
    appendElectronLog('backend already ready')
    return
  } catch {
    // Start our own backend below.
  }

  const python = await findPython()
  await runCommand(python.command, [...python.prefix, '-m', 'alembic', 'upgrade', 'head'], 120000)
  await runCommand(python.command, [...python.prefix, 'seed.py'], 120000)
  backendProcess = spawnLogged(python.command, [
    ...python.prefix,
    '-m',
    'uvicorn',
    'app.main:app',
    '--host',
    '127.0.0.1',
    '--port',
    String(BACKEND_PORT),
  ])
  backendProcess.on('exit', (code) => appendElectronLog(`backend exited with code ${code}`))
  backendProcess.on('error', (error) => appendElectronLog(`backend process error: ${error.message}`))
  await waitForBackend()
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
    port: BACKEND_PORT,
    method: request.method,
    path: request.url,
    headers: {
      ...request.headers,
      host: `127.0.0.1:${BACKEND_PORT}`,
      origin: `http://127.0.0.1:${FRONTEND_PORT}`,
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
  const dist = frontendDistDir()
  if (!fs.existsSync(path.join(dist, 'index.html'))) {
    throw new Error(`Frontend de produção não encontrado em ${dist}. Execute npm run build antes de abrir o app desktop.`)
  }
  staticServer = http.createServer((request, response) => {
    const reqUrl = new URL(request.url || '/', `http://127.0.0.1:${FRONTEND_PORT}`)
    if (reqUrl.pathname.startsWith('/api/') || reqUrl.pathname === '/ready' || reqUrl.pathname === '/health') {
      proxyToBackend(request, response)
      return
    }
    const decoded = decodeURIComponent(reqUrl.pathname)
    const safePath = path.normalize(decoded).replace(/^(\.\.[/\\])+/, '')
    let filePath = path.join(dist, safePath === '/' ? 'index.html' : safePath)
    if (!filePath.startsWith(dist) || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
      filePath = path.join(dist, 'index.html')
    }
    response.writeHead(200, {
      'Content-Type': contentType(filePath),
      'Cache-Control': filePath.endsWith('index.html') ? 'no-cache' : 'public, max-age=31536000, immutable',
    })
    fs.createReadStream(filePath).pipe(response)
  })
  return new Promise((resolve, reject) => {
    staticServer.once('error', reject)
    staticServer.listen(FRONTEND_PORT, '127.0.0.1', () => {
      appendElectronLog(`frontend server ready: ${FRONTEND_PORT}`)
      resolve()
    })
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
  mainWindow.loadURL(`http://127.0.0.1:${FRONTEND_PORT}`)
  mainWindow.once('ready-to-show', () => {
    if (splashWindow && !splashWindow.isDestroyed()) splashWindow.close()
    mainWindow.show()
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
  errorWindow.loadFile(path.join(__dirname, 'error.html'))
}

async function bootApplication() {
  if (startupInProgress) return
  startupInProgress = true
  try {
    ensureRuntimeDirs()
    appendElectronLog('boot start')
    createSplashWindow()
    const startedAt = Date.now()
    await startBackend()
    await startFrontendServer()
    const elapsed = Date.now() - startedAt
    if (elapsed < MIN_SPLASH_MS) {
      await new Promise((resolve) => setTimeout(resolve, MIN_SPLASH_MS - elapsed))
    }
    createMainWindow()
    appendElectronLog('boot success')
  } catch (error) {
    appendElectronLog(`boot failed: ${error.stack || error.message}`)
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
  if (backendProcess && backendProcess.pid) {
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(backendProcess.pid), '/t', '/f'], { windowsHide: true })
    } else {
      backendProcess.kill('SIGTERM')
    }
  }
  backendProcess = null
}

ipcMain.handle('desktop:retry', async () => {
  if (errorWindow && !errorWindow.isDestroyed()) errorWindow.close()
  stopChildren()
  await bootApplication()
  return true
})

ipcMain.handle('desktop:openLogs', async () => {
  ensureRuntimeDirs()
  await shell.openPath(logDir)
  return true
})

ipcMain.handle('desktop:close', () => {
  app.quit()
})

ipcMain.handle('desktop:info', () => ({
  appName: APP_NAME,
  version: app.getVersion(),
  backendPort: BACKEND_PORT,
  frontendPort: FRONTEND_PORT,
  error: lastStartupError ? String(lastStartupError.message || lastStartupError) : null,
  logDir,
}))

app.whenReady().then(bootApplication)
app.on('before-quit', stopChildren)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) bootApplication()
})
