<template>
  <div class="tasks">
    <h2>⚙️ 爬虫任务管理</h2>

    <div class="task-status-card">
      <div class="status-row">
        <span class="status-label">当前状态</span>
        <span class="status-badge" :class="task.status">{{ statusText }}</span>
      </div>
      <div class="status-row">
        <span class="status-label">定时规则</span>
        <span class="status-value">{{ task.schedule }}</span>
      </div>
      <div class="status-row">
        <span class="status-label">最后运行</span>
        <span class="status-value">{{ task.last_run || '从未运行' }}</span>
      </div>
    </div>

    <div v-if="task.last_result" class="result-card">
      <div class="result-title">上次运行结果</div>
      <div class="result-row">返回码: <span :class="task.last_result.returncode === 0 ? 'ok' : 'fail'">{{ task.last_result.returncode }}</span></div>
      <div v-if="task.last_result.stdout" class="result-output">{{ task.last_result.stdout }}</div>
      <div v-if="task.last_result.stderr" class="result-output error">{{ task.last_result.stderr }}</div>
    </div>

    <div class="actions">
      <button class="btn-start" :disabled="task.status === 'running'" @click="start">
        ▶ 启动爬取
      </button>
      <button class="btn-stop" :disabled="task.status !== 'running'" @click="stop">
        ⏹ 停止
      </button>
    </div>

    <div v-if="actionMsg" class="action-msg" :class="actionMsgType">{{ actionMsg }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api/index.js'

const task = ref({ status: 'idle', last_run: null, last_result: null, schedule: '0 9 * * *' })
const actionMsg = ref('')
const actionMsgType = ref('info')

const statusText = computed(() => ({
  idle: '空闲',
  running: '运行中',
  stopping: '停止中',
}[task.value.status] || task.value.status))

function showMsg(msg, type = 'info') {
  actionMsg.value = msg
  actionMsgType.value = type
  setTimeout(() => { actionMsg.value = '' }, 5000)
}

async function loadStatus() {
  try {
    const res = await api.taskStatus()
    task.value = res
  } catch (e) {
    showMsg('加载状态失败: ' + e.message, 'error')
  }
}

async function start() {
  if (task.value.status === 'running') return
  showMsg('正在启动爬取，请稍候...', 'info')
  try {
    const res = await api.taskStart()
    showMsg('爬取完成，返回码: ' + res.code, res.code === 0 ? 'ok' : 'error')
    await loadStatus()
  } catch (e) {
    showMsg('启动失败: ' + e.message, 'error')
  }
}

async function stop() {
  try {
    await api.taskStop()
    showMsg('停止信号已发送', 'info')
    await loadStatus()
  } catch (e) {
    showMsg('停止失败: ' + e.message, 'error')
  }
}

onMounted(() => loadStatus())
</script>

<style scoped>
.tasks h2 { margin-top: 0; }
.task-status-card, .result-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px; }
.status-row { display: flex; align-items: center; gap: 16px; padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
.status-row:last-child { border-bottom: none; }
.status-label { color: #888; font-size: 13px; min-width: 80px; }
.status-badge { padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: bold; }
.status-badge.idle { background: #e8f5e9; color: #2e7d32; }
.status-badge.running { background: #fff3e0; color: #e65100; }
.status-badge.stopping { background: #fce4ec; color: #c62828; }
.status-value { font-size: 14px; color: #333; font-family: monospace; }
.result-title { font-weight: bold; margin-bottom: 12px; color: #333; }
.result-row { font-size: 13px; margin: 4px 0; }
.result-output { margin-top: 10px; padding: 10px; background: #f5f5f5; border-radius: 4px; font-size: 12px; font-family: monospace; white-space: pre-wrap; max-height: 150px; overflow-y: auto; }
.result-output.error { background: #fff3f3; color: #c62828; }
.ok { color: #2e7d32; }
.fail { color: #c62828; }
.actions { display: flex; gap: 16px; }
.btn-start, .btn-stop { padding: 12px 32px; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; font-weight: bold; }
.btn-start { background: #2e7d32; color: white; }
.btn-start:disabled { background: #a5d6a7; cursor: not-allowed; }
.btn-stop { background: #c62828; color: white; }
.btn-stop:disabled { background: #ffcdd2; cursor: not-allowed; }
.action-msg { margin-top: 16px; padding: 12px; border-radius: 6px; font-size: 14px; }
.action-msg.info { background: #e3f2fd; color: #1565c0; }
.action-msg.ok { background: #e8f5e9; color: #2e7d32; }
.action-msg.error { background: #ffebee; color: #c62828; }
</style>