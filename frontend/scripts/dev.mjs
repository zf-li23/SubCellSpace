import net from 'node:net'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const frontendRoot = resolve(__dirname, '..')
const repoRoot = resolve(frontendRoot, '..')
// Try to detect Python from the project venv, then fall back to system PATH
import { accessSync, constants } from 'node:fs'

function detectPython() {
  // 1. Check .venv in repo root (pip venv)
  const venvPython = resolve(repoRoot, '.venv/bin/python')
  try {
    accessSync(venvPython, constants.X_OK)
    return venvPython
  } catch { /* not found */ }

  // 2. Explicit override, then the active conda env (conda activate subcellspace)
  for (const candidate of [process.env.SUBCELLSPACE_PYTHON, process.env.CONDA_PREFIX && resolve(process.env.CONDA_PREFIX, 'bin/python')]) {
    if (!candidate) continue
    try {
      accessSync(candidate, constants.X_OK)
      return candidate
    } catch { /* not found */ }
  }

  // 3. Fall back to PATH
  return 'python3'
}

const pythonBin = detectPython()
console.log(`[launcher] using Python: ${pythonBin}`)

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

function spawnProcess(command, args, cwd, label, extraEnv = {}) {
  const child = spawn(command, args, {
    cwd,
    stdio: 'inherit',
    env: { ...process.env, ...extraEnv },
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
    { TF_CPP_MIN_LOG_LEVEL: '3', TF_ENABLE_ONEDNN_OPTS: '0' },
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
