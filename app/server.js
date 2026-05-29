import express from 'express'
import yaml from 'js-yaml'
import nunjucks from 'nunjucks'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import dotenv from 'dotenv'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..')

dotenv.config({ path: path.join(ROOT, '.env') })
nunjucks.configure({ autoescape: false })

const app = express()
app.use(express.json({ limit: '20mb' }))
app.use(express.static(path.join(__dirname, 'dist')))

// ── helpers ────────────────────────────────────────────────────────────────

function settings() {
  return {
    llmBaseUrl: process.env.LLM_BASE_URL || 'http://localhost:11434',
    llmModel: process.env.LLM_MODEL || 'mistral',
    llmApiKey: process.env.LLM_API_KEY || 'none',
  }
}

function loadConfig(configFile) {
  const configPath = path.join(ROOT, configFile)
  const config = yaml.load(fs.readFileSync(configPath, 'utf-8'))
  const testsPath = path.join(ROOT, config.tests)
  const tests = yaml.load(fs.readFileSync(testsPath, 'utf-8'))
  return { config, tests, testsFile: config.tests }
}

function renderPrompt(template, vars, envVars) {
  return nunjucks.renderString(template, { ...vars, env: envVars })
}

function checkAssertion(output, assertion) {
  const text = output.trim()
  const value = String(assertion.value)
  switch (assertion.type) {
    case 'equals':    return text === value
    case 'icontains': return text.toLowerCase().includes(value.toLowerCase())
    case 'contains':  return text.includes(value)
    default:          return null
  }
}

async function callLLM(renderedPrompt, modelConfig, { retries = 0, retryDelayMs = 1000 } = {}) {
  const { llmBaseUrl, llmModel, llmApiKey } = settings()
  for (let attempt = 0; attempt <= retries; attempt++) {
    if (attempt > 0) await new Promise(r => setTimeout(r, retryDelayMs * 2 ** (attempt - 1)))
    const res = await fetch(`${llmBaseUrl}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${llmApiKey}`,
      },
      body: JSON.stringify({
        model: llmModel,
        messages: [{ role: 'user', content: renderedPrompt }],
        temperature: modelConfig?.temperature ?? 0,
        max_tokens: modelConfig?.max_tokens ?? 2000,
      }),
      signal: AbortSignal.timeout(120_000),
    })
    if (!res.ok) {
      const body = await res.text()
      if (res.status === 429 && attempt < retries) continue
      throw new Error(`LLM ${res.status}: ${body}`)
    }
    return res.json()
  }
}

async function runSingleTest(test, config, retryOpts = {}) {
  const { llmModel } = settings()
  const template = config.prompts[0].raw
  const modelConfig = config.providers[0].config ?? {}
  const rendered = renderPrompt(template, test.vars, { LLM_MODEL: llmModel })

  const data = await callLLM(rendered, modelConfig, retryOpts)
  const output = data.choices?.[0]?.message?.content ?? ''

  const assertions = (test.assert ?? []).map(a => ({
    type: a.type,
    value: a.value,
    pass: checkAssertion(output, a),
  }))

  return {
    output,
    pass: assertions.length > 0 && assertions.every(a => a.pass !== false),
    assertions,
    usage: data.usage ?? null,
    renderedPrompt: rendered,
  }
}

// ── routes ─────────────────────────────────────────────────────────────────

app.get('/api/settings', (_, res) => {
  const { llmBaseUrl, llmModel, llmApiKey } = settings()
  res.json({ llmBaseUrl, llmModel, hasApiKey: llmApiKey !== 'none' })
})

app.get('/api/llm/ping', async (_, res) => {
  const { llmBaseUrl, llmApiKey } = settings()
  try {
    const r = await fetch(`${llmBaseUrl}/v1/models`, {
      headers: { Authorization: `Bearer ${llmApiKey}` },
      signal: AbortSignal.timeout(5_000),
    })
    const body = r.ok ? await r.json() : null
    res.json({ ok: r.ok, status: r.status, models: body?.data?.map(m => m.id) ?? [] })
  } catch (e) {
    res.json({ ok: false, error: e.message })
  }
})

app.get('/api/configs', (_, res) => {
  try {
    const files = fs.readdirSync(ROOT)
      .filter(f => /^promptfooconfig.*\.yaml$/.test(f))
      .sort()
    res.json(files)
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

app.get('/api/config', (req, res) => {
  try {
    const { config, tests } = loadConfig(req.query.file ?? 'promptfooconfig.yaml')
    res.json({ config, tests })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

app.put('/api/config/test/:i', (req, res) => {
  try {
    const file = req.query.file ?? 'promptfooconfig.yaml'
    const { tests, testsFile } = loadConfig(file)
    tests[Number(req.params.i)] = req.body
    fs.writeFileSync(
      path.join(ROOT, testsFile),
      yaml.dump(tests, { allow_unicode: true, default_flow_style: false, sort_keys: false, lineWidth: 200 }),
    )
    res.json({ ok: true })
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

app.post('/api/run/:i', async (req, res) => {
  try {
    const { config, tests } = loadConfig(req.query.file ?? 'promptfooconfig.yaml')
    const retryOpts = {
      retries: Number(req.query.retries ?? 0),
      retryDelayMs: Number(req.query.retryDelayMs ?? 1000),
    }
    const result = await runSingleTest(tests[Number(req.params.i)], config, retryOpts)
    res.json(result)
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
})

// Server-Sent Events — run all tests sequentially, stream results in real time
app.get('/api/run-all', async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream')
  res.setHeader('Cache-Control', 'no-cache')
  res.setHeader('Connection', 'keep-alive')
  res.flushHeaders()

  const send = (data) => res.write(`data: ${JSON.stringify(data)}\n\n`)

  try {
    const { config, tests } = loadConfig(req.query.file ?? 'promptfooconfig.yaml')
    const retryOpts = {
      retries: Number(req.query.retries ?? 0),
      retryDelayMs: Number(req.query.retryDelayMs ?? 1000),
    }
    for (let i = 0; i < tests.length; i++) {
      try {
        const result = await runSingleTest(tests[i], config, retryOpts)
        send({ index: i, ...result })
      } catch (e) {
        send({ index: i, error: e.message, pass: false, output: '' })
      }
    }
  } catch (e) {
    send({ error: e.message })
  }

  send({ done: true })
  res.end()
})

// SPA fallback — serve index.html for any non-API route in production
app.get('*', (_, res) => {
  const distIndex = path.join(__dirname, 'dist', 'index.html')
  if (fs.existsSync(distIndex)) {
    res.sendFile(distIndex)
  } else {
    res.status(404).send('Lance `npm run build` ou utilise le mode dev (`npm run dev`).')
  }
})

const PORT = process.env.APP_PORT || 3000
app.listen(PORT, () => console.log(`✓  Promptfoo Runner  →  http://localhost:${PORT}`))
