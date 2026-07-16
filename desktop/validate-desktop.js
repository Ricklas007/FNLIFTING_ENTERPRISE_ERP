const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')
const required = [
  'desktop/main.js',
  'desktop/preload.js',
  'desktop/splash.html',
  'desktop/error.html',
  'desktop/assets/icon.ico',
  'desktop/assets/icon.png',
  'desktop/assets/splash-logo.png',
  'desktop/runtime/backend.js',
  'backend/desktop_runtime.py',
  'frontend/dist/index.html',
  'scripts/build-desktop-backend.ps1',
  'scripts/test-backend-standalone.ps1',
]

const missing = required.filter((item) => !fs.existsSync(path.join(root, item)))
if (missing.length) {
  console.error('Desktop build validation failed. Missing files:')
  for (const item of missing) console.error(`- ${item}`)
  process.exit(1)
}

const main = fs.readFileSync(path.join(root, 'desktop/main.js'), 'utf8')
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'))
const securityChecks = [
  'contextIsolation: true',
  'nodeIntegration: false',
  'preload:',
  'requestSingleInstanceLock',
]
for (const check of securityChecks) {
  if (!main.includes(check)) {
    console.error(`Desktop security validation failed: ${check}`)
    process.exit(1)
  }
}

const resources = JSON.stringify(pkg.build?.extraResources ?? [])
if (resources.includes('backend/.venv') || resources.includes('backend\\.venv')) {
  console.error('Desktop packaging validation failed: backend .venv must not be packaged.')
  process.exit(1)
}

console.log('Desktop build validation passed.')
