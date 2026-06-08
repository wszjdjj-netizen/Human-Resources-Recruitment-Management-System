# 招聘管理系统 - 部署指南

## 📋 目录

- [部署前准备](#部署前准备)
- [方案一：Docker Compose 部署（推荐）](#方案一docker-compose-部署推荐)
- [方案二：传统部署](#方案二传统部署)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [安全建议](#安全建议)

---

## 部署前准备

### 必须完成的配置

#### 1. 获取 AI API 密钥

系统的核心功能（简历解析、职位匹配）依赖 AI 服务，必须配置 API 密钥：

**DeepSeek（推荐，性价比高）**
- 注册地址：https://platform.deepseek.com
- 注册后在"API Keys"页面创建密钥
- 费用：约 ¥1/百万tokens

**通义千问（国内访问快）**
- 注册地址：https://dashscope.aliyun.com
- 在控制台获取 API Key
- 配置时修改 `AI_ENDPOINT=https://dashscope.aliyuncs.com/compatible-mode/v1`

#### 2. 生成安全密钥

JWT 认证需要强随机密钥，使用以下命令生成：

```bash
# Linux/Mac
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Windows PowerShell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

复制输出的密钥，后续配置时使用。

---

## 方案一：Docker Compose 部署（推荐）

### 适用场景
- 快速部署
- 简化运维
- 适合小型团队
- 自动配置数据库和网络

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+

### 部署步骤

#### 1. 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
# 复制示例文件
cp backend/.env.example .env

# 编辑配置
nano .env
```

修改以下配置：

```env
# 数据库配置（Docker会自动使用PostgreSQL）
DATABASE_URL=postgresql://recruitment_user:your_db_password@postgres:5432/recruitment

# JWT密钥（替换为刚才生成的密钥）
SECRET_KEY=zTzS0KObFOlvP1fYwx5OGn0YmQG7RvIyCD_IyAIUaQ0
CREDENTIAL_ENCRYPTION_KEY=replace-with-another-random-secret-key

# AI接口默认配置（不建议填全局密钥；每个用户登录后到「AI配置」页面保存自己的 Key）
AI_ENDPOINT=https://api.deepseek.com/v1
AI_API_KEY=
AI_MODEL=deepseek-chat
ALLOW_AI_ENV_FALLBACK=false

# 注册控制（公网建议设置邀请码，防止随意注册刷 AI 费用）
ALLOW_PUBLIC_REGISTRATION=true
REGISTRATION_INVITE_CODE=replace-with-your-invite-code

# CORS配置（填入实际域名）
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

#### 2. 构建并启动服务

```bash
# 构建镜像
docker-compose build

# 启动服务（后台运行）
docker-compose up -d

# 查看日志
docker-compose logs -f
```

#### 3. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 测试后端API
curl http://localhost:8000/api/health

# 访问前端
浏览器打开 http://localhost
```

#### 4. 常用操作

```bash
# 停止服务
docker-compose stop

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f backend

# 进入容器
docker-compose exec backend bash

# 备份数据库
docker-compose exec postgres pg_dump -U recruitment_user recruitment > backup.sql

# 恢复数据库
docker-compose exec -T postgres psql -U recruitment_user recruitment < backup.sql

# 完全清理（删除所有数据）
docker-compose down -v
```

---

## 方案二：传统部署

### 适用场景
- 需要自定义配置
- 使用云服务商的托管数据库
- 已有运维基础设施

### 前置要求

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Nginx 1.20+

### 部署步骤

#### 1. 安装依赖

**后端**

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

**前端**

```bash
cd frontend

# 安装依赖
npm install

# 构建生产版本
npm run build
```

#### 2. 配置数据库

```bash
# 创建数据库
sudo -u postgres psql
CREATE DATABASE recruitment;
CREATE USER recruitment_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE recruitment TO recruitment_user;
\q

# 修改 backend/.env
DATABASE_URL=postgresql://recruitment_user:your_password@localhost:5432/recruitment
```

#### 3. 配置 Nginx

创建 `/etc/nginx/sites-available/recruitment`：

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # 前端静态文件
    root /var/www/recruitment/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 25m;
    }

    # 上传文件代理
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/recruitment /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 4. 配置 Systemd 服务

创建 `/etc/systemd/system/recruitment-backend.service`：

```ini
[Unit]
Description=Recruitment Backend Service
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/recruitment/backend
Environment="PATH=/var/www/recruitment/backend/.venv/bin"
ExecStart=/var/www/recruitment/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable recruitment-backend
sudo systemctl start recruitment-backend
sudo systemctl status recruitment-backend
```

#### 5. 配置 HTTPS（使用 Let's Encrypt）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com

# 自动续期（Certbot会自动配置）
sudo certbot renew --dry-run
```

---

## 配置说明

### 环境变量详解

| 变量名 | 说明 | 示例 | 必填 |
|--------|------|------|------|
| `DATABASE_URL` | 数据库连接字符串 | `postgresql://user:pass@host:5432/db` | ✅ |
| `SECRET_KEY` | JWT签名密钥 | 随机字符串（32+字符） | ✅ |
| `AI_ENDPOINT` | AI服务端点 | `https://api.deepseek.com/v1` | ✅ |
| `AI_API_KEY` | 全局AI兜底密钥（默认不启用；推荐留空，让每个用户自己配置） | `sk-xxx` | ❌ |
| `ALLOW_AI_ENV_FALLBACK` | 是否允许未配置用户使用全局AI密钥 | `false` | ❌ |
| `REGISTRATION_INVITE_CODE` | 注册邀请码，公网建议配置 | `your-code` | ❌ |
| `AI_MODEL` | AI模型名称 | `deepseek-chat` | ✅ |
| `CORS_ORIGINS` | 允许的跨域源 | `https://yourdomain.com` | ✅ |
| `UPLOAD_DIR` | 上传目录 | `uploads` | ❌ |
| `MAX_UPLOAD_SIZE_MB` | 上传大小限制(MB) | `20` | ❌ |
| `JWT_EXPIRE_DAYS` | JWT过期天数 | `7` | ❌ |

### 数据库连接示例

**SQLite（仅开发）**
```
DATABASE_URL=sqlite:///./recruitment.db
```

**PostgreSQL（生产推荐）**
```
DATABASE_URL=postgresql://user:password@localhost:5432/recruitment
```

**MySQL**
```
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/recruitment
```

---

## 常见问题

### 1. AI功能报401错误

**原因**：AI_API_KEY未配置或无效

**解决**：
1. 检查 `.env` 文件中的 `AI_API_KEY` 是否填写正确
2. 或在前端"AI配置"页面重新配置
3. 重启后端服务：`docker-compose restart backend`

### 2. 前端无法调用后端API

**原因**：CORS配置错误

**解决**：
1. 检查 `.env` 中 `CORS_ORIGINS` 是否包含前端域名
2. 确保没有多余空格，多个域名用逗号分隔
3. 重启后端服务

### 3. 文件上传失败

**原因**：文件大小超限或目录权限问题

**解决**：
```bash
# 检查上传目录权限
ls -la backend/uploads

# 修复权限
chmod 755 backend/uploads

# 修改大小限制（backend/.env）
MAX_UPLOAD_SIZE_MB=50
```

### 4. 数据库连接失败

**原因**：数据库未启动或连接字符串错误

**解决**：
```bash
# 检查PostgreSQL状态
docker-compose ps postgres

# 检查数据库日志
docker-compose logs postgres

# 测试连接
docker-compose exec postgres psql -U recruitment_user -d recruitment
```

### 5. Playwright浏览器启动失败

**原因**：缺少依赖库

**解决**：
```bash
# Docker部署会自动安装
# 传统部署需手动安装
playwright install-deps chromium
```

---

## 安全建议

### ✅ 必须执行

1. **更换默认密钥**
   - ❌ `SECRET_KEY=your-secret-key-change-in-production`
   - ✅ 使用 `secrets.token_urlsafe(32)` 生成

2. **使用HTTPS**
   - 生产环境必须启用SSL/TLS
   - 使用Let's Encrypt免费证书

3. **限制CORS源**
   - ❌ `CORS_ORIGINS=*`
   - ✅ `CORS_ORIGINS=https://yourdomain.com`

4. **定期备份数据**
   ```bash
   # 每天自动备份
   0 2 * * * docker-compose exec -T postgres pg_dump -U recruitment_user recruitment > /backup/recruitment_$(date +\%Y\%m\%d).sql
   ```

5. **保护敏感文件**
   ```bash
   # 确保.env文件不被提交
   chmod 600 backend/.env
   # 检查.gitignore
   cat .gitignore | grep .env
   ```

### 🔒 推荐执行

1. **限制数据库访问**
   - 仅允许本地或私有网络连接
   - 使用强密码

2. **配置防火墙**
   ```bash
   # 仅开放必要端口
   ufw allow 22/tcp    # SSH
   ufw allow 80/tcp    # HTTP
   ufw allow 443/tcp   # HTTPS
   ufw enable
   ```

3. **启用日志监控**
   ```bash
   # 查看错误日志
   docker-compose logs --tail=100 backend | grep ERROR
   # 持续监控
   docker-compose logs -f backend
   ```

4. **定期更新依赖**
   ```bash
   # 更新Python依赖
   pip list --outdated
   # 更新Node依赖
   npm outdated
   ```

---

## 监控与维护

### 健康检查

```bash
# 后端健康检查
curl http://localhost:8000/api/health

# 前端健康检查
curl http://localhost/

# Docker健康状态
docker-compose ps
```

### 日志查看

```bash
# 查看所有日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs postgres

# 实时日志
docker-compose logs -f --tail=50 backend
```

### 性能优化

1. **数据库索引**
   - 系统已配置基础索引
   - 根据查询模式添加自定义索引

2. **静态文件CDN**
   - 将前端静态资源上传到CDN
   - 修改 `frontend/vite.config.js` 配置base路径

3. **数据库连接池**
   - 已在代码中配置
   - 根据并发量调整池大小

---

## 升级指南

### 更新代码

```bash
# 拉取最新代码
git pull origin main

# Docker部署
docker-compose down
docker-compose build
docker-compose up -d

# 传统部署
systemctl stop recruitment-backend
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build
systemctl start recruitment-backend
```

### 数据库迁移

```bash
# 备份数据
docker-compose exec postgres pg_dump -U recruitment_user recruitment > backup_before_update.sql

# 应用迁移（如有新的数据库脚本）
docker-compose exec backend python -c "from app.database import init_db; init_db()"
```

---

## 技术支持

如遇到问题，请检查：
1. [常见问题](#常见问题) 章节
2. 系统日志：`docker-compose logs backend`
3. GitHub Issues：https://github.com/your-repo/issues

---

## 附录

### A. 推荐的服务器配置

**最低配置（开发/测试）**
- CPU: 2核
- 内存: 4GB
- 硬盘: 20GB
- 带宽: 1Mbps

**推荐配置（生产）**
- CPU: 4核
- 内存: 8GB
- 硬盘: 50GB SSD
- 带宽: 5Mbps

### B. 云服务商推荐

**阿里云**
- ECS + RDS + OSS
- 适合国内用户
- 价格：约¥200/月起

**腾讯云**
- CVM + TencentDB
- 学生优惠力度大
- 价格：约¥180/月起

**AWS**
- EC2 + RDS
- 全球部署
- 价格：约$30/月起

### C. 成本估算

**月度运营成本（小型团队）**
- 服务器：¥200
- 数据库：¥100（或包含在服务器中）
- AI调用：¥50（约5000万tokens）
- 域名+SSL：¥10
- **总计：约¥360/月**

---

*最后更新：2026-06-06*
