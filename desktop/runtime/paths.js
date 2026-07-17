const fs = require('fs')
const path = require('path')

function rootDir(app) {
  return app.isPackaged ? process.resourcesPath : path.resolve(__dirname, '..', '..')
}

function frontendDistDir(app) {
  return path.join(rootDir(app), 'frontend', 'dist')
}

function backendStandaloneExe(app) {
  const packaged = path.join(process.resourcesPath, 'backend', 'FNLiftingBackend', 'FNLiftingBackend.exe')
  const devBuilt = path.join(rootDir(app), 'backend-dist', 'FNLiftingBackend', 'FNLiftingBackend.exe')
  return app.isPackaged ? packaged : devBuilt
}

function backendDevEntrypoint(app) {
  return path.join(rootDir(app), 'backend', 'desktop_runtime.py')
}

function backendDevPython(app) {
  return process.env.FNLIFTING_PYTHON || path.join(rootDir(app), 'backend', '.venv', 'Scripts', 'python.exe')
}

function createRuntimePaths(app) {
  const base = process.env.FNLIFTING_USER_DATA_DIR
    ? path.resolve(process.env.FNLIFTING_USER_DATA_DIR)
    : app.getPath('userData')
  const paths = {
    base,
    data: path.join(base, 'data'),
    uploads: path.join(base, 'uploads'),
    signatures: path.join(base, 'uploads', 'signatures'),
    certificates: path.join(base, 'certificates'),
    reports: path.join(base, 'reports'),
    invoices: path.join(base, 'invoices'),
    receipts: path.join(base, 'receipts'),
    backups: path.join(base, 'backups'),
    logs: path.join(base, 'logs'),
    config: path.join(base, 'config'),
    temp: path.join(base, 'temp'),
    exports: path.join(base, 'exports'),
    maps: path.join(base, 'maps'),
    mapCache: path.join(base, 'map-cache'),
    gps: path.join(base, 'gps'),
    attachments: path.join(base, 'attachments'),
  }
  for (const value of Object.values(paths)) fs.mkdirSync(value, { recursive: true })
  return paths
}

function sqliteUrl(filePath) {
  return `sqlite:///${path.resolve(filePath).replace(/\\/g, '/')}`
}

module.exports = {
  rootDir,
  frontendDistDir,
  backendStandaloneExe,
  backendDevEntrypoint,
  backendDevPython,
  createRuntimePaths,
  sqliteUrl,
}
