<template>
  <div class="repos">
    <h2>📦 GitHub 仓库</h2>

    <!-- 搜索筛选栏 -->
    <div class="toolbar">
      <input v-model="keyword" placeholder="搜索仓库名称/描述..." class="search-input" @input="debounceSearch" />
      <select v-model="language" class="select-input" @change="load">
        <option value="">全部语言</option>
        <option v-for="l in langOptions" :key="l.language" :value="l.language">{{ l.language }}</option>
      </select>
      <select v-model="sortBy" class="select-input" @change="load">
        <option value="stars_today">今日热度</option>
        <option value="stars">总星数</option>
        <option value="forks">Fork数</option>
      </select>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <template v-else>
      <div class="total-hint">共 {{ total }} 条结果</div>
      <div class="repo-list">
        <div v-for="repo in items" :key="repo.id" class="repo-card">
          <div class="repo-header">
            <a :href="repo.repo_url" target="_blank" class="repo-name">{{ repo.repo_full_name }}</a>
            <span class="lang-tag">{{ repo.language }}</span>
          </div>
          <p class="repo-desc">{{ repo.description || '无描述' }}</p>
          <div class="repo-stats">
            <span>⭐ {{ repo.stars?.toLocaleString() }}</span>
            <span class="hot">▲ {{ repo.stars_today }}</span>
            <span>🍴 {{ repo.forks }}</span>
            <button class="sim-btn" @click="showSimilar(repo)">相似推荐</button>
          </div>
          <!-- 相似推荐 -->
          <div v-if="similarRepoId === repo.id" class="similar-panel">
            <div v-if="simLoading" class="sim-loading">查找中...</div>
            <div v-else-if="similarItems.length === 0" class="sim-empty">无相似仓库 (调整 threshold 试试)</div>
            <div v-else v-for="s in similarItems" :key="s.id" class="sim-item">
              <a :href="'https://github.com/' + s.repo_full_name" target="_blank">{{ s.repo_full_name }}</a>
              <span>距离 {{ s.hamming_distance }} 相似度 {{ (s.similarity_score * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div class="pagination">
        <button :disabled="offset === 0" @click="changePage(-1)">上一页</button>
        <span>第 {{ Math.floor(offset / limit) + 1 }} / {{ Math.ceil(total / limit) || 1 }} 页</span>
        <button :disabled="offset + limit >= total" @click="changePage(1)">下一页</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/index.js'

const items = ref([])
const total = ref(0)
const offset = ref(0)
const limit = ref(20)
const keyword = ref('')
const language = ref('')
const sortBy = ref('stars_today')
const langOptions = ref([])
const loading = ref(true)
const error = ref('')
const similarRepoId = ref(null)
const similarItems = ref([])
const simLoading = ref(false)

let searchTimer = null

function debounceSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { offset.value = 0; load() }, 400)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.repos({
      keyword: keyword.value,
      language: language.value,
      sort_by: sortBy.value,
      limit: limit.value,
      offset: offset.value,
    })
    items.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function loadLangs() {
  try {
    const res = await api.repoLanguages()
    langOptions.value = res.items || []
  } catch {}
}

async function showSimilar(repo) {
  if (similarRepoId.value === repo.id) {
    similarRepoId.value = null
    return
  }
  similarRepoId.value = repo.id
  simLoading.value = true
  similarItems.value = []
  try {
    const res = await api.repoSimilar(repo.id, { threshold: 30, limit: 5 })
    similarItems.value = res.items || []
  } catch {
    similarItems.value = []
  } finally {
    simLoading.value = false
  }
}

function changePage(delta) {
  offset.value = Math.max(0, offset.value + delta * limit.value)
  load()
}

onMounted(() => { load(); loadLangs() })
</script>

<style scoped>
.repos h2 { margin-top: 0; }
.toolbar { display: flex; gap: 10px; margin-bottom: 16px; }
.search-input { flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
.select-input { padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
.total-hint { margin-bottom: 12px; color: #888; font-size: 13px; }
.repo-list { display: flex; flex-direction: column; gap: 12px; }
.repo-card { background: white; border-radius: 8px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.repo-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.repo-name { font-size: 16px; font-weight: bold; color: #3498db; text-decoration: none; }
.repo-name:hover { text-decoration: underline; }
.lang-tag { background: #e8f5e9; color: #2e7d32; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.repo-desc { font-size: 13px; color: #666; margin: 8px 0; line-height: 1.5; }
.repo-stats { display: flex; align-items: center; gap: 16px; font-size: 13px; color: #888; margin-top: 8px; }
.repo-stats .hot { color: #e74c3c; font-weight: bold; }
.sim-btn { margin-left: auto; padding: 4px 12px; border: 1px solid #3498db; background: white; color: #3498db; border-radius: 4px; cursor: pointer; font-size: 12px; }
.sim-btn:hover { background: #3498db; color: white; }
.similar-panel { margin-top: 12px; padding-top: 12px; border-top: 1px solid #eee; }
.sim-loading, .sim-empty { font-size: 13px; color: #888; }
.sim-item { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 13px; }
.sim-item a { color: #3498db; text-decoration: none; }
.sim-item a:hover { text-decoration: underline; }
.pagination { display: flex; align-items: center; gap: 16px; margin-top: 20px; justify-content: center; }
.pagination button { padding: 6px 16px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer; }
.pagination button:disabled { color: #ccc; cursor: not-allowed; }
.loading, .error { text-align: center; padding: 60px; color: #888; }
.error { color: #e74c3c; }
</style>