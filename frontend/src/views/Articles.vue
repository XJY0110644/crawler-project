<template>
  <div class="articles">
    <h2>📝 SegmentFault 文章</h2>

    <div class="toolbar">
      <input v-model="keyword" placeholder="搜索标题/摘要..." class="search-input" @input="debounceSearch" />
      <select v-model="sortBy" class="select-input" @change="load">
        <option value="views">按阅读</option>
        <option value="votes">按点赞</option>
        <option value="comments">按评论</option>
      </select>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <template v-else>
      <div class="total-hint">共 {{ total }} 条结果</div>
      <div class="article-list">
        <div v-for="a in items" :key="a.article_id" class="article-card">
          <div class="article-header">
            <a :href="a.url" target="_blank" class="article-title">{{ a.title }}</a>
          </div>
          <div class="article-meta">
            <span>👤 {{ a.author_name || '匿名' }}</span>
            <span>👁️ {{ a.views?.toLocaleString() }}</span>
            <span>👍 {{ a.votes }}</span>
            <span>💬 {{ a.comments }}</span>
          </div>
          <p class="article-summary">{{ a.summary || '' }}</p>
          <div class="article-actions">
            <button class="sim-btn" @click="showSimilar(a)">相似文章</button>
          </div>
          <div v-if="similarArticleId === a.article_id" class="similar-panel">
            <div v-if="simLoading" class="sim-loading">查找中...</div>
            <div v-else-if="similarItems.length === 0" class="sim-empty">无相似文章</div>
            <div v-else v-for="s in similarItems" :key="s.article_id" class="sim-item">
              <a :href="s.url" target="_blank">{{ s.title }}</a>
              <span>距离 {{ s.hamming_distance }} 相似度 {{ (s.similarity_score * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>
      </div>

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
const sortBy = ref('views')
const loading = ref(true)
const error = ref('')
const similarArticleId = ref(null)
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
    const res = await api.articles({ keyword: keyword.value, sort_by: sortBy.value, limit: limit.value, offset: offset.value })
    items.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function showSimilar(a) {
  if (similarArticleId.value === a.article_id) {
    similarArticleId.value = null
    return
  }
  similarArticleId.value = a.article_id
  simLoading.value = true
  similarItems.value = []
  try {
    const res = await api.articleSimilar(a.article_id, { threshold: 15, limit: 5 })
    similarItems.value = res.items || []
  } catch { similarItems.value = [] }
  finally { simLoading.value = false }
}

function changePage(delta) {
  offset.value = Math.max(0, offset.value + delta * limit.value)
  load()
}

onMounted(() => load())
</script>

<style scoped>
.articles h2 { margin-top: 0; }
.toolbar { display: flex; gap: 10px; margin-bottom: 16px; }
.search-input { flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
.select-input { padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
.total-hint { margin-bottom: 12px; color: #888; font-size: 13px; }
.article-list { display: flex; flex-direction: column; gap: 12px; }
.article-card { background: white; border-radius: 8px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.article-title { font-size: 16px; font-weight: bold; color: #3498db; text-decoration: none; }
.article-title:hover { text-decoration: underline; }
.article-meta { display: flex; gap: 16px; font-size: 13px; color: #888; margin: 8px 0; }
.article-summary { font-size: 13px; color: #666; line-height: 1.5; margin: 8px 0; }
.article-actions { margin-top: 8px; }
.sim-btn { padding: 4px 12px; border: 1px solid #3498db; background: white; color: #3498db; border-radius: 4px; cursor: pointer; font-size: 12px; }
.sim-btn:hover { background: #3498db; color: white; }
.similar-panel { margin-top: 12px; padding-top: 12px; border-top: 1px solid #eee; }
.sim-loading, .sim-empty { font-size: 13px; color: #888; }
.sim-item { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 13px; }
.sim-item a { color: #3498db; text-decoration: none; max-width: 60%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pagination { display: flex; align-items: center; gap: 16px; margin-top: 20px; justify-content: center; }
.pagination button { padding: 6px 16px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer; }
.pagination button:disabled { color: #ccc; cursor: not-allowed; }
.loading, .error { text-align: center; padding: 60px; color: #888; }
.error { color: #e74c3c; }
</style>