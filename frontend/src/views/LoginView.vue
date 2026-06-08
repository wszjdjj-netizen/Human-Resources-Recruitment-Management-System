<template>
  <div class="auth-container">
    <div class="auth-shell">
      <section class="auth-panel">
        <span class="eyebrow">AI Recruiting OS</span>
        <h1>招聘管理系统</h1>
        <p class="auth-subtitle">用智能解析、匹配评分和人才标签，把简历筛选变成一张清晰的决策界面。</p>
        <p class="future-line">未来的招聘与应聘，可能是 <span>agent to agent</span></p>

        <div class="form-area">
          <div class="input-group">
            <span class="input-icon"><el-icon :size="18"><User /></el-icon></span>
            <input
              v-model="form.username"
              class="native-input"
              placeholder="请输入用户名或邮箱"
              autocomplete="username"
            />
          </div>
          <div class="input-group">
            <span class="input-icon"><el-icon :size="18"><Lock /></el-icon></span>
            <input
              v-model="form.password"
              class="native-input"
              type="password"
              placeholder="请输入密码"
              autocomplete="current-password"
              @keyup.enter="handleLogin"
            />
          </div>
          <button
            class="login-btn"
            :disabled="loading"
            @click="handleLogin"
          >
            <span v-if="loading" class="spinner"></span>
            {{ loading ? '登录中...' : '登录' }}
          </button>
        </div>

        <p class="auth-link">
          还没有账号？<router-link to="/register">立即注册</router-link>
        </p>
      </section>

    </div>

    <div class="galaxy-bg">
      <div class="star" style="top:8%;left:6%;width:3px;height:3px;animation-delay:0s;"></div>
      <div class="star" style="top:12%;left:18%;width:2px;height:2px;animation-delay:1.2s;"></div>
      <div class="star" style="top:22%;left:4%;width:4px;height:4px;animation-delay:0.6s;"></div>
      <div class="star" style="top:35%;left:10%;width:2px;height:2px;animation-delay:2.1s;"></div>
      <div class="star" style="top:45%;left:3%;width:3px;height:3px;animation-delay:0.9s;"></div>
      <div class="star" style="top:55%;left:15%;width:2px;height:2px;animation-delay:1.8s;"></div>
      <div class="star" style="top:68%;left:7%;width:4px;height:4px;animation-delay:0.3s;"></div>
      <div class="star" style="top:78%;left:20%;width:2px;height:2px;animation-delay:2.5s;"></div>
      <div class="star" style="top:88%;left:5%;width:3px;height:3px;animation-delay:1.5s;"></div>
      <div class="star" style="top:95%;left:16%;width:2px;height:2px;animation-delay:0.7s;"></div>
      <div class="star" style="top:5%;left:82%;width:3px;height:3px;animation-delay:1.1s;"></div>
      <div class="star" style="top:15%;left:92%;width:2px;height:2px;animation-delay:0.4s;"></div>
      <div class="star" style="top:25%;left:85%;width:4px;height:4px;animation-delay:2.0s;"></div>
      <div class="star" style="top:38%;left:96%;width:2px;height:2px;animation-delay:0.8s;"></div>
      <div class="star" style="top:48%;left:88%;width:3px;height:3px;animation-delay:1.6s;"></div>
      <div class="star" style="top:58%;left:95%;width:2px;height:2px;animation-delay:0.2s;"></div>
      <div class="star" style="top:72%;left:83%;width:4px;height:4px;animation-delay:2.3s;"></div>
      <div class="star" style="top:82%;left:94%;width:2px;height:2px;animation-delay:1.0s;"></div>
      <div class="star" style="top:92%;left:86%;width:3px;height:3px;animation-delay:0.5s;"></div>
      <div class="star" style="top:3%;left:50%;width:2px;height:2px;animation-delay:1.9s;"></div>
      <div class="star" style="top:8%;left:38%;width:3px;height:3px;animation-delay:0.1s;"></div>
      <div class="star" style="top:18%;left:62%;width:2px;height:2px;animation-delay:1.3s;"></div>
      <div class="star" style="top:30%;left:55%;width:4px;height:4px;animation-delay:0.6s;"></div>
      <div class="star" style="top:42%;left:48%;width:2px;height:2px;animation-delay:2.2s;"></div>
      <div class="star" style="top:52%;left:65%;width:3px;height:3px;animation-delay:0.9s;"></div>
      <div class="star" style="top:62%;left:52%;width:2px;height:2px;animation-delay:1.7s;"></div>
      <div class="star" style="top:75%;left:60%;width:4px;height:4px;animation-delay:0.4s;"></div>
      <div class="star" style="top:85%;left:45%;width:2px;height:2px;animation-delay:2.4s;"></div>
      <div class="star" style="top:95%;left:70%;width:3px;height:3px;animation-delay:1.4s;"></div>

      <span class="float-text" style="top:10%;left:12%;font-size:15px;animation-delay:0s;">自动发布职位</span>
      <span class="float-text" style="top:18%;left:76%;font-size:17px;animation-delay:-2.4s;">智能简历筛选</span>
      <span class="float-text" style="top:28%;left:4%;font-size:14px;animation-delay:-5s;">多渠道自动 sourcing</span>
      <span class="float-text" style="top:32%;left:86%;font-size:16px;animation-delay:-1.2s;">人才画像自动构建</span>
      <span class="float-text" style="top:42%;left:18%;font-size:18px;animation-delay:-3.6s;">人岗匹配自动评分</span>
      <span class="float-text" style="top:48%;left:72%;font-size:13px;animation-delay:-0.8s;">面试自动邀约</span>
      <span class="float-text" style="top:58%;left:6%;font-size:15px;animation-delay:-4.5s;">招聘流程自动化</span>
      <span class="float-text" style="top:62%;left:84%;font-size:17px;animation-delay:-1.8s;">候选人自动跟进</span>
      <span class="float-text" style="top:72%;left:22%;font-size:14px;animation-delay:-6s;">智能人才推荐</span>
      <span class="float-text" style="top:78%;left:66%;font-size:16px;animation-delay:-3s;">招聘数据自动分析</span>
      <span class="float-text" style="top:85%;left:8%;font-size:13px;animation-delay:-5.5s;">自动淘汰低匹配简历</span>
      <span class="float-text" style="top:88%;left:78%;font-size:15px;animation-delay:-2s;">人才库自动更新</span>
      <span class="float-text" style="top:5%;left:44%;font-size:14px;animation-delay:-4s;">JD 智能生成</span>
      <span class="float-text" style="top:15%;left:54%;font-size:16px;animation-delay:-0.5s;">招聘助手自动回复</span>
      <span class="float-text" style="top:25%;left:34%;font-size:13px;animation-delay:-3.2s;">标签体系自动打标</span>
      <span class="float-text" style="top:38%;left:56%;font-size:15px;animation-delay:-1.5s;">漏斗转化自动追踪</span>
      <span class="float-text" style="top:52%;left:40%;font-size:14px;animation-delay:-5.2s;">Offer 决策辅助</span>
      <span class="float-text" style="top:68%;left:46%;font-size:16px;animation-delay:-2.8s;">招聘效果自动复盘</span>
      <span class="float-text" style="top:75%;left:36%;font-size:13px;animation-delay:-0.3s;">高潜人才自动识别</span>
      <span class="float-text" style="top:92%;left:50%;font-size:14px;animation-delay:-4.8s;">入职流程自动推进</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

async function handleLogin() {
  if (loading.value) return

  if (!form.username.trim()) {
    ElMessage.warning('请输入用户名或邮箱')
    return
  }
  if (!form.password.trim()) {
    ElMessage.warning('请输入密码')
    return
  }

  loading.value = true
  try {
    await authStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    await new Promise(r => setTimeout(r, 50))
    router.push('/')
  } catch (e) {
    const msg = e?.response?.data?.detail || '登录失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at 20% 30%, rgba(79, 124, 255, 0.10), transparent 35%),
    radial-gradient(circle at 80% 70%, rgba(18, 182, 203, 0.08), transparent 35%),
    radial-gradient(circle at 50% 50%, rgba(79, 124, 255, 0.04), transparent 50%),
    linear-gradient(180deg, #f5f9ff, #eef4ff);
}

.galaxy-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.star {
  position: absolute;
  border-radius: 50%;
  background: rgba(79, 124, 255, 0.65);
  box-shadow: 0 0 10px rgba(79, 124, 255, 0.45);
  animation: starPulse 4s ease-in-out infinite;
}

@keyframes starPulse {
  0%, 100% { opacity: 0.35; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1.4); }
}

.float-text {
  position: absolute;
  font-size: 16px;
  font-weight: 600;
  color: rgba(47, 99, 255, 0.38);
  letter-spacing: 0.08em;
  white-space: nowrap;
  user-select: none;
  animation: floatDrift 10s ease-in-out infinite;
  text-shadow: 0 0 24px rgba(79, 124, 255, 0.20);
}

.float-text:nth-child(odd) {
  animation-duration: 12s;
}

.float-text:nth-child(3n) {
  animation-duration: 14s;
}

@keyframes floatDrift {
  0%, 100% { transform: translate(0, 0); }
  25% { transform: translate(8px, -14px); }
  50% { transform: translate(-6px, -8px); }
  75% { transform: translate(12px, 6px); }
}

.auth-shell {
  position: relative;
  z-index: 2;
  width: min(440px, 100%);
}

.auth-panel {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(200, 216, 248, 0.55);
  border-radius: 20px;
  background:
    linear-gradient(145deg, rgba(232, 242, 255, 0.92), rgba(220, 234, 255, 0.72)),
    rgba(228, 238, 252, 0.78);
  backdrop-filter: blur(24px) saturate(1.3);
  box-shadow:
    0 4px 6px rgba(42, 62, 110, 0.02),
    0 12px 24px rgba(42, 62, 110, 0.04),
    0 32px 64px rgba(42, 62, 110, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
  will-change: transform;
  padding: 52px 44px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.auth-panel::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(120deg, transparent 0 46%, rgba(255, 255, 255, 0.45) 52%, transparent 60%);
}

.auth-panel > * {
  position: relative;
  z-index: 1;
}

.eyebrow {
  display: block;
  text-align: center;
  color: #2f63ff;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  text-align: center;
  color: #172033;
  font-size: 34px;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.015em;
}

.auth-subtitle {
  max-width: 360px;
  margin: 14px 0 18px;
  text-align: center;
  color: #667085;
  font-size: 14px;
  line-height: 1.8;
}

.future-line {
  max-width: 370px;
  margin: 0 0 30px;
  text-align: center;
  color: transparent;
  font-size: clamp(15px, 1.45vw, 18px);
  font-weight: 700;
  line-height: 1.65;
  letter-spacing: 0.03em;
  background: linear-gradient(120deg, #172033 0%, #2f63ff 48%, #12b6cb 100%);
  -webkit-background-clip: text;
  background-clip: text;
  text-shadow: 0 12px 30px rgba(79, 124, 255, 0.16);
}

.future-line span {
  display: inline-block;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: lowercase;
}

.form-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.input-group {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 14px;
  z-index: 1;
  display: flex;
  align-items: center;
  color: #7b8ba7;
}

.native-input {
  width: 100%;
  height: 48px;
  padding: 0 16px 0 42px;
  color: #172033;
  font-size: 15px;
  outline: none;
  border: 1px solid rgba(78, 92, 130, 0.12);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: inset 0 1px 2px rgba(44, 62, 98, 0.04), 0 4px 12px rgba(44, 62, 98, 0.04);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.native-input:focus {
  border-color: rgba(79, 124, 255, 0.45);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 0 0 4px rgba(79, 124, 255, 0.10), inset 0 1px 2px rgba(44, 62, 98, 0.02);
}

.native-input::placeholder {
  color: #98a2b3;
}

.login-btn {
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #4f7cff, #12b6cb);
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 12px 28px rgba(79, 124, 255, 0.28);
  transition: transform 0.15s ease, box-shadow 0.2s ease;
  will-change: transform;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 14px 32px rgba(79, 124, 255, 0.34);
}

.login-btn:disabled {
  cursor: not-allowed;
  opacity: 0.72;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.auth-link {
  margin-top: 22px;
  color: #667085;
  font-size: 14px;
  text-align: center;
}

.auth-link a {
  color: #2f63ff;
  font-weight: 600;
  text-decoration: none;
}

@media (max-width: 520px) {
  .auth-container {
    padding: 20px;
  }

  .auth-panel {
    padding: 36px 24px;
    border-radius: 16px;
  }

  h1 {
    font-size: 28px;
  }

  .float-text {
    display: none;
  }
}
</style>
