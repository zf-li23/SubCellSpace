import net from 'node:net'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const frontendRoot = resolve(__dirname, '..')
const repoRoot = resolve(frontendRoot, '..')
const pythonBin = '/home/zf-li23/miniconda3/envs/zf-li23/bin/python'

let backendProcess = null
let frontendProcess = null

function isPortOpen(port, host = '127.0.0.1') {
  return new Promise((resolvePromise) => {
    const socket = net.createConnection({ port, host })

    const finish = (value) => {
      socket.removeAllListeners()
      socket.end()
      resolvePromise(value)
    }

    socket.once('connect', () => finish(true))
    socket.once('error', () => finish(false))
  })
}

async function waitForPort(port, timeoutMs = 30000) {
  const startedAt = Date.now()
  while (Date.now() - startedAt < timeoutMs) {
    if (await isPortOpen(port)) {
      return true
    }
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 500))
  }
  return false
}

function spawnProcess(command, args, cwd, label) {
  const child = spawn(command, args, {
    cwd,
    stdio: 'inherit',
    env: process.env,
  })

  child.on('exit', (code, signal) => {
    if (signal || code !== 0) {
      const status = signal ? `signal ${signal}` : `code ${code}`
      console.log(`[${label}] exited with ${status}`)
    }
  })

  return child
}

async function startBackendIfNeeded() {
  if (await isPortOpen(8000)) {
    console.log('[launcher] backend already available on 127.0.0.1:8000')
    return
  }

  console.log('[launcher] starting backend on 127.0.0.1:8000')
  backendProcess = spawnProcess(
    pythonBin,
    ['-m', 'uvicorn', 'src.api_server:app', '--host', '127.0.0.1', '--port', '8000'],
    repoRoot,
    'backend',
  )

  const ready = await waitForPort(8000)
  if (!ready) {
    throw new Error('Backend did not become ready on port 8000')
  }
}

function shutdown() {
  for (const child of [frontendProcess, backendProcess]) {
    if (child && !child.killed) {
      child.kill('SIGTERM')
    }
  }
}

process.on('SIGINT', () => {
  shutdown()
  process.exit(130)
})

process.on('SIGTERM', () => {
  shutdown()
  process.exit(143)
})

try {
  await startBackendIfNeeded()
  frontendProcess = spawnProcess('vite', ['--host', '127.0.0.1', '--port', '5173'], frontendRoot, 'frontend')
} catch (error) {
  console.error('[launcher] failed to start development environment')
  console.error(error)
  shutdown()
  process.exit(1)
}
