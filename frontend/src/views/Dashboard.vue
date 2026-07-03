<template>
  <div class="dashboard">
    <h2>📊 数据总览</h2>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <template v-else>
      <!-- 统计卡片 -->
      <div class="cards">
        <div class="card">
          <div class="card-label">GitHub 仓库总数</div>
          <div class="card-value">{{ overview.github?.total_repos ?? '-' }}</div>
        </div>
        <div class="card">
          <div class="card-label">GitHub 总星数</div>
          <div class="card-value">{{ overview.github?.total_stars?.toLocaleString() ?? '-' }}</div>
        </div>
        <div class="card">
          <div class="card-label">今日新增星数</div>
          <div class="card-value hot">{{ overview.github?.today_stars?.toLocaleString() ?? '-' }}</div>
        </div>
        <div class="card">
          <div class="card-label">SF 文章总数</div>
          <div class="card-value">{{ overview.segmentfault?.total_articles ?? '-' }}</div>
        </div>
        <div class="card">
          <div class="card-label">技术栈种类</div>
          <div class="card-value">{{ overview.github?.languages ?? '-' }}</div>
        </div>
        <div class="card">
          <div class="card-label">SF 作者数</div>
          <div class="card-value">{{ overview.segmentfault?.total_authors ?? '-' }}</div>
        </div>
      </div>

      <!-- 今日最热 -->
      <h3>🔥 今日最热 TOP10</h3>
      <div class="trending-list">
        <div v-for="repo in trending" :key="repo.id" class="trending-item">
          <a :href="repo.repo_url" target="_blank" class="repo-name">{{ repo.repo_full_name }}</a>
          <span class="lang-tag">{{ repo.language }}</span>
          <span class="stars-today">▲{{ repo.stars_today }}</span>
        </div>
      </div>

      <!-- 语言分布 -->
      <h3>📈 语言分布</h3>
      <div class="lang-list">
        <div v-for="lang in languages" :key="lang.language" class="lang-item">
          <span class="lang-name">{{ lang.language }}</span>
          <span class="lang-count">{{ lang.count }} 仓库</span>
          <div class="lang-bar-wrap">
            <div class="lang-bar" :style="{ width: lang.count / maxLangCount * 100 + '%' }"></div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { api } from '../api/index.js'

const overview = ref({})
const trending = ref([])
const languages = ref([])
const loading = ref(true)
const error = ref('')

const maxLangCount = computed(() => Math.max(...languages.value.map(l => l.count), 1))

onMounted(async () => {
  try {
    const [ov, tr, lang] = await Promise.all([
      api.statsOverview(),
      api.statsTrending(),
      api.statsLanguages(),
    ])
    overview.value = ov
    trending.value = tr.items || []
    languages.value = lang.items || []
  } catch (e) {
    error.value = '加载失败: ' + e.message
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.dashboard h2 { margin-top: 0; margin-bottom: 20px; }
.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 30px; }
.card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.card-label { color: #888; font-size: 13px; margin-bottom: 8px; }
.card-value { font-size: 28px; font-weight: bold; color: #333; }
.card-value.hot { color: #e74c3c; }
h3 { margin: 20px 0 12px; color: #333; }
.trending-list { background: white; border-radius: 8px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.trending-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.trending-item:last-child { border-bottom: none; }
.repo-name { flex: 1; color: #3498db; text-decoration: none; font-size: 14px; font-weight: 500; }
.repo-name:hover { text-decoration: underline; }
.lang-tag { background: #e8f5e9; color: #2e7d32; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.stars-today { color: #e74c3c; font-weight: bold; font-size: 14px; }
.lang-list { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.lang-item { background: white; border-radius: 8px; padding: 12px 16px; display: flex; align-items: center; gap: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.lang-name { font-weight: bold; min-width: 80px; color: #333; }
.lang-count { font-size: 13px; color: #888; min-width: 80px; }
.lang-bar-wrap { flex: 1; height: 6px; background: #eee; border-radius: 3px; }
.lang-bar { height: 100%; background: #3498db; border-radius: 3px; }
.loading, .error { text-align: center; padding: 60px; color: #888; }
.error { color: #e74c3c; }
</style>