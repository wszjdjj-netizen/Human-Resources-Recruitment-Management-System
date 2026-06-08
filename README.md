# 招聘管理系统

智能简历筛选与人才池管理平台。上传简历 → AI自动解析 → 与岗位JD匹配打分 → 人才池排名管理。

## 功能概览

- **职位管理**：创建/编辑招聘职位，填写完整JD（用于AI匹配）
- **简历上传**：批量上传PDF/Word简历，自动提取文本
- **AI解析**：调用大模型API将简历解析为结构化数据（姓名、联系方式、教育/工作经历、技能）
- **智能匹配**：AI对比简历与JD，输出匹配分数（0-100）+详细分析报告
- **人才池**：按职位筛选候选人，默认仅展示已匹配候选人，支持评分、技能标签、复制联系方式、批量删除和状态管理
- **首页统计**：职位总数与开放职位状态统一由后端汇总，和职位管理口径一致
- **候选人操作台**：候选人详情与上传后的管理区采用卡片式布局，避免横向滚动，评分、标签、状态、电话/邮箱复制都能直接操作
- **个人资料**：登录后可修改用户名、邮箱、公司名称，也支持修改密码
- **平台搜人**：支持配置招聘平台登录态、创建搜人任务、按岗位JD匹配候选人、入库并生成个性化打招呼消息

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python FastAPI + SQLAlchemy + SQLite |
| 前端 | Vue 3 + Element Plus + Pinia + Axios |
| AI | 兼容OpenAI API格式（DeepSeek/通义千问/GPT等） |
| 数据库 | SQLite（可切换PostgreSQL） |

## 快速开始

### 1. 环境要求

- Python 3.12+（推荐3.12，更高版本可能有包兼容问题）
- Node.js 18+
- AI API Key（推荐 [DeepSeek](https://platform.deepseek.com) 或 [通义千问](https://dashscope.aliyun.com)）

### 2. 配置AI接口

```bash
cd backend
cp .env.example .env
# 编辑 .env 文件，填入你的AI API信息
```

### 3. 启动后端

在新的 CMD 窗口运行：

```bat
cd /d D:\网站\backend && .\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

如果还没有安装过后端依赖，先执行：

```bat
cd /d D:\网站\backend
# 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

后端运行在 http://localhost:8000

### 4. 启动前端

在另一个新的 CMD 窗口运行：

```bat
cd /d D:\网站\frontend && npm run dev
```

如果还没有安装过前端依赖，先执行：

```bat
cd /d D:\网站\frontend
npm install
```

前端运行在 http://localhost:5173

### 5. 使用

1. 打开浏览器访问 http://localhost:5173
2. 注册HR账号并登录
3. 在「职位管理」创建招聘职位（填写JD）
4. 在职位详情页上传简历（支持批量PDF/Word）
5. 点击「一键匹配」对候选人进行AI打分
6. 在「人才池」查看所有候选人的排名和详细信息
7. 在候选人卡片上可直接复制电话/邮箱、批量删除、快速改状态，支持全选批量删除
8. 在「平台搜人」配置平台登录态，创建搜人任务，按JD跨平台搜索并自动导入候选人
9. 点击顶部用户名或左侧「个人资料」修改账号资料

## 平台搜人上线路线

当前系统已预留真实平台搜人架构：

- 平台连接：`/api/sourcing/platforms` 保存平台账号登录态（当前支持Cookie演示，生产建议接入加密存储和授权流程）
- 搜人任务：`/api/sourcing/tasks` 保存岗位、平台、关键词、城市、最低匹配分、目标人数和打招呼模板
- 任务运行：`/api/sourcing/tasks/{id}/run` 统一执行入口，当前内置演示适配器，后续可逐个平台接入浏览器自动化适配器
- 人才入库：符合阈值的候选人写入人才池、技能标签和匹配结果
- 打招呼：开启后生成待发送消息，建议上线阶段先人工确认，再接自动发送

合规提醒：真实招聘平台通常有登录风控、访问频率限制和服务条款要求。公网部署时不要用服务器IP高频抓取，推荐采用用户授权登录态、低频任务、人工确认和可审计发送记录。

## 项目结构

```
website/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI入口
│   │   ├── config.py         # 配置管理
│   │   ├── database.py       # 数据库连接
│   │   ├── models/           # ORM数据模型
│   │   ├── schemas/          # Pydantic请求/响应模型
│   │   ├── routers/          # API路由
│   │   ├── services/         # 业务逻辑(AI客户端/简历解析/匹配)
│   │   ├── middleware/       # JWT认证中间件
│   │   └── utils/            # 工具函数(PDF/Word文本提取)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/            # 页面组件
│   │   ├── components/       # 可复用组件
│   │   ├── api/              # API请求封装
│   │   ├── stores/           # Pinia状态管理
│   │   ├── router/           # 路由配置
│   │   └── utils/            # 常量/工具函数
│   └── package.json
└── README.md
```

## API文档

启动后端后访问 http://localhost:8000/docs 查看自动生成的Swagger API文档。

## 最近更新

- 全站 UI 简约化重设计：字体权重标准化（统一 400/500/600/700，移除 650/750/760/780 等非标准值）、间距增加 20-50% 提升呼吸感、圆角升级到 12-16px、backdrop-filter 从 22-26px 优化到 20px、伪元素光效透明度微调，玻璃质感与蓝色调主题完全保留
- 首页“开放职位”统计已切换为后端统一汇总接口，口径与职位管理一致
- 人才池改为卡片式候选人操作台，去掉横向拖动条，重点信息直接可见
- 候选人电话/邮箱支持一键复制
- 候选人支持批量删除
- 人才池默认仅显示已匹配候选人
- 首页增加职位总数和开放职位双统计口径，避免和职位管理混淆
- 候选人列表与职位详情页都增加了全选批量删除和更紧凑的状态/操作区
- 全站玻璃质感、发光层次和卡片节奏已统一更新
- 新增「个人资料」页面，可更新基础资料和密码
- 新增「平台搜人」任务工作台：平台连接、关键词/城市/阈值配置、任务运行、入库结果和个性化打招呼模板
- 个人资料更新增加POST兼容接口，避免部分代理或旧缓存环境对PUT提示“方法不允许”
- 简历解析和AI匹配的角色提示已加强；匹配增加关键词兜底评分，AI接口临时失败时不会阻断整批筛选
- README启动方式更新为前端/后端文件夹下可直接复制的一行CMD命令

## CloudBase 部署信息

| 项目 | 详情 |
|------|------|
| 环境 ID | `rlzp-d2g1q3sa247f84e3e` |
| 环境 Alias | `rlzp` |
| 区域 | ap-shanghai |
| 套餐 | 体验版 (baas_trial) |
| **前端访问地址** | **https://rlzp-d2g1q3sa247f84e3e-1324232839.tcloudbaseapp.com/** |
| 静态托管 Bucket | `3cfb-static-rlzp-d2g1q3sa247f84e3e-1324232839` |

### CloudBase 控制台入口

- 环境概览: https://tcb.cloud.tencent.com/dev?envId=rlzp-d2g1q3sa247f84e3e#/overview
- 静态托管: https://tcb.cloud.tencent.com/dev?envId=rlzp-d2g1q3sa247f84e3e#/static-hosting
- 云数据库: https://tcb.cloud.tencent.com/dev?envId=rlzp-d2g1q3sa247f84e3e#/db/doc
- 云函数: https://tcb.cloud.tencent.com/dev?envId=rlzp-d2g1q3sa247f84e3e#/scf
- 云存储: https://tcb.cloud.tencent.com/dev?envId=rlzp-d2g1q3sa247f84e3e#/storage

> **注意**: 当前前端为纯静态部署，API 请求 `/api` 路径需要后端服务支持。如需完整功能，需额外部署后端到 Cloud Run 或其他服务器，并修改 `config.js` 中的 `API_BASE_URL` 指向后端地址。
