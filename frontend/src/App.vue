<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="logo">🕷️ CrawlerDB</div>
      <nav>
        <router-link to="/dashboard">📊 总览</router-link>
        <router-link to="/repos">📦 仓库</router-link>
        <router-link to="/articles">📝 文章</router-link>
        <router-link to="/tasks">⚙️ 任务</router-link>
      </nav>
      <div class="backend-url">
        API: <code>{{ apiBase }}</code>
      </div>
    </aside>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const apiBase = ref(import.meta.env.VITE_API_BASE || 'http://localhost:8000')
</script>

<style scoped>
.layout { display: flex; height: 100vh; }
.sidebar {
  width: 200px;
  background: #1a1a2e;
  color: #eee;
  padding: 20px 0;
  display: flex;
  flex-direction: column;
}
.logo { font-size: 18px; font-weight: bold; padding: 0 20px 30px; color: #00d4ff; }
nav a {
  display: block;
  padding: 12px 20px;
  color: #aaa;
  text-decoration: none;
  transition: 0.2s;
}
nav a:hover, nav a.router-link-active { background: #16213e; color: #00d4ff; }
.backend-url {
  margin-top: auto;
  padding: 16px 20px;
  font-size: 11px;
  color: #555;
}
.backend-url code { color: #888; }
.content { flex: 1; overflow-y: auto; background: #f5f7fa; padding: 24px; }
</style>