const BASE = '/api'

async function get(path) {
  const r = await fetch(BASE + path)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

async function post(path, body) {
  const r = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export const api = {
  // 统计总览
  statsOverview: () => get('/stats/overview'),
  statsTrending: () => get('/stats/trending'),
  statsLanguages: () => get('/stats/languages'),

  // 仓库
  repos: (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return get('/repos' + (q ? '?' + q : ''))
  },
  repoLanguages: () => get('/repos/languages'),
  repoSimilar: (id, params = {}) => {
    const q = new URLSearchParams({ ...params }).toString()
    return get(`/repos/${id}/similar?${q}`)
  },

  // 文章
  articles: (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return get('/articles' + (q ? '?' + q : ''))
  },
  articleSimilar: (id, params = {}) => {
    const q = new URLSearchParams({ ...params }).toString()
    return get(`/articles/${id}/similar?${q}`)
  },

  // 任务
  taskStatus: () => get('/tasks'),
  taskStart: () => post('/tasks/start', {}),
  taskStop: () => post('/tasks/stop', {}),
}