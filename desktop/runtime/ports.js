const http = require('http')

function canUse(port) {
  return new Promise((resolve) => {
    const server = http.createServer()
    server.once('error', () => resolve(false))
    server.once('listening', () => server.close(() => resolve(true)))
    server.listen(port, '127.0.0.1')
  })
}

async function choosePort(preferred, start, end) {
  const requested = Number(preferred)
  if (requested && await canUse(requested)) return requested
  for (let port = start; port <= end; port += 1) {
    if (await canUse(port)) return port
  }
  throw new Error(`Nenhuma porta livre entre ${start} e ${end}.`)
}

module.exports = { choosePort }
