const crypto = require('crypto')
const fs = require('fs')
const path = require('path')
const { spawn } = require('child_process')
const {
  backendDevEntrypoint,
  backendDevPython,
  backendStandaloneExe,
  rootDir,
  sqliteUrl,
} = require('./paths')

function readOrCreateSecret(paths, name) {
  const file = path.join(paths.config, name)
  if (fs.existsSync(file)) return fs.readFileSync(file, 'utf8').trim()
  const value = crypto.randomBytes(48).toString('hex')
  fs.writeFileSync(file, value, { encoding: 'utf8', mode: 0o600 })
  return value
}

class BackendManager {
  constructor({ app, paths, logManager, backendPort, frontendPort }) {
    this.app = app
    this.paths = paths
    this.logManager = logManager
    this.backendPort = backendPort
    this.frontendPort = frontendPort
    this.child = null
  }

  env() {
    return {
      ...process.env,
      APP_NAME: 'FNLIFTING Enterprise ERP',
      APP_VERSION: this.app.getVersion(),
      APP_ENV: 'desktop',
      ENVIRONMENT: 'desktop',
      DESKTOP_MODE: 'true',
      DEBUG: 'false',
      AUTO_CREATE_SCHEMA: 'true',
      SECURITY_HEADERS_ENABLED: 'true',
      HOST: '127.0.0.1',
      PORT: String(this.backendPort),
      DATA_DIR: this.paths.data,
      UPLOAD_DIR: this.paths.uploads,
      CERTIFICATE_DIR: this.paths.certificates,
      REPORT_DIR: this.paths.reports,
      INVOICE_DIR: this.paths.invoices,
      RECEIPT_DIR: this.paths.receipts,
      BACKUP_DIR: this.paths.backups,
      LOG_DIR: this.paths.logs,
      EXPORT_DIR: this.paths.exports,
      MAP_DIR: this.paths.maps,
      MAP_CACHE_DIR: this.paths.mapCache,
      TEMP_DIR: this.paths.temp,
      ATTACHMENT_DIR: this.paths.attachments,
      DATABASE_URL: sqliteUrl(path.join(this.paths.data, 'fnlifting.db')),
      SECRET_KEY: readOrCreateSecret(this.paths, 'secret.key'),
      BACKUP_ENCRYPTION_KEY: readOrCreateSecret(this.paths, 'backup.key'),
      CORS_ORIGINS: `http://127.0.0.1:${this.frontendPort},http://localhost:${this.frontendPort}`,
      ALLOWED_HOSTS: '127.0.0.1,localhost',
    }
  }

  commandArgs(command) {
    const standalone = backendStandaloneExe(this.app)
    if (fs.existsSync(standalone)) {
      return { command: standalone, args: [command], cwd: path.dirname(standalone), mode: 'standalone' }
    }
    if (this.app.isPackaged) {
      throw new Error(`Backend standalone não encontrado em ${standalone}. O pacote está incompleto.`)
    }
    const python = backendDevPython(this.app)
    if (!fs.existsSync(python)) throw new Error(`Python de desenvolvimento não encontrado em ${python}.`)
    return {
      command: python,
      args: [backendDevEntrypoint(this.app), command],
      cwd: path.join(rootDir(this.app), 'backend'),
      mode: 'development-python',
    }
  }

  runCommand(command, timeoutMs, logName = 'migration') {
    const spec = this.commandArgs(command)
    this.logManager.write('startup', `backend command ${command} via ${spec.mode}`)
    return new Promise((resolve, reject) => {
      const out = this.logManager.stream(logName)
      const err = this.logManager.stream(logName)
      const child = spawn(spec.command, spec.args, {
        cwd: spec.cwd,
        env: this.env(),
        windowsHide: true,
        stdio: ['ignore', out, err],
      })
      let settled = false
      const timer = setTimeout(() => {
        if (settled) return
        settled = true
        child.kill()
        reject(new Error(`Timeout ao executar backend ${command}.`))
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
        code === 0 ? resolve() : reject(new Error(`Backend ${command} terminou com código ${code}. Consulte ${this.paths.logs}.`))
      })
    })
  }

  async migrateAndSeed() {
    await this.runCommand('migrate', 180000, 'migration')
    await this.runCommand('seed', 180000, 'startup')
  }

  startServe() {
    const spec = this.commandArgs('serve')
    const out = this.logManager.stream('backend')
    const err = this.logManager.stream('backend')
    this.child = spawn(spec.command, spec.args, {
      cwd: spec.cwd,
      env: this.env(),
      windowsHide: true,
      stdio: ['ignore', out, err],
    })
    this.child.on('exit', (code) => this.logManager.write('backend', `backend exited with code ${code}`))
    this.child.on('error', (error) => this.logManager.write('backend', `backend process error: ${error.message}`))
  }

  stop() {
    if (!this.child || !this.child.pid) return
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(this.child.pid), '/t', '/f'], { windowsHide: true })
    } else {
      this.child.kill('SIGTERM')
    }
    this.child = null
  }
}

module.exports = { BackendManager }
