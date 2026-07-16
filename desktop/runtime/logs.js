const fs = require('fs')
const path = require('path')

class LogManager {
  constructor(paths) {
    this.paths = paths
    this.files = {
      desktop: path.join(paths.logs, 'desktop.log'),
      backend: path.join(paths.logs, 'backend.log'),
      migration: path.join(paths.logs, 'migration.log'),
      startup: path.join(paths.logs, 'startup.log'),
    }
  }

  write(name, message) {
    const file = this.files[name] || this.files.desktop
    fs.appendFileSync(file, `[${new Date().toISOString()}] ${message}\n`, 'utf8')
  }

  stream(name) {
    const file = this.files[name] || this.files.backend
    return fs.openSync(file, 'a')
  }
}

module.exports = { LogManager }
