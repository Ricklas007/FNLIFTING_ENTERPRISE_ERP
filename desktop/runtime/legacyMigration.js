const fs = require('fs')
const path = require('path')

function isSQLite(file) {
  try {
    if (!fs.existsSync(file) || fs.statSync(file).size < 100) return false
    const header = Buffer.alloc(16)
    const fd = fs.openSync(file, 'r')
    fs.readSync(fd, header, 0, 16, 0)
    fs.closeSync(fd)
    return header.toString('utf8') === 'SQLite format 3\u0000'
  } catch {
    return false
  }
}

function migrateLegacyDatabase({ app, runtimePaths, rootDir, logManager }) {
  const destination = path.join(runtimePaths.data, 'fnlifting.db')
  if (fs.existsSync(destination)) {
    logManager.write('startup', 'legacy migration skipped: userData database already exists')
    return { migrated: false, reason: 'destination-exists' }
  }

  const candidates = [
    path.join(rootDir, 'backend', 'data', 'fnlifting.db'),
    path.join(process.resourcesPath || rootDir, 'backend', 'data', 'fnlifting.db'),
    path.join(app.getPath('appData'), 'fnlifting-enterprise-erp', 'data', 'fnlifting.db'),
  ]
  for (const source of candidates) {
    if (!isSQLite(source)) continue
    const backup = path.join(runtimePaths.backups, `legacy-source-${Date.now()}.sqlite3`)
    fs.copyFileSync(source, backup)
    fs.copyFileSync(source, destination)
    fs.writeFileSync(path.join(runtimePaths.config, 'legacy-migration.json'), JSON.stringify({
      migratedAt: new Date().toISOString(),
      source,
      destination,
      backup,
    }, null, 2), 'utf8')
    logManager.write('startup', `legacy database migrated from ${source}`)
    return { migrated: true, source, backup }
  }
  logManager.write('startup', 'legacy migration skipped: no legacy sqlite database found')
  return { migrated: false, reason: 'not-found' }
}

module.exports = { migrateLegacyDatabase }
