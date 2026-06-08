# Local Browser Runner

用于部署后的网站与使用者电脑上的本地浏览器执行端之间的桥接。

BOSS 直聘等招聘平台风控较强，不建议让云服务器直接代抓。当前设计是：
线上网站只负责任务、审批、日志和入库；真实平台登录、验证码、搜索和打招呼动作都在使用者自己的电脑上用可见浏览器完成。

## 推荐启动方式

Windows 用户不需要打开命令行，直接双击项目根目录的：

```text
start-local-runner.bat
```

首次运行时它会自动创建 Python 环境、安装依赖、安装 Playwright Chromium，并启动本地执行器。后续再双击会直接启动。

如果希望在网页里点「一键唤起执行器」，先双击一次：

```text
register-runner-protocol.bat
```

它会给当前 Windows 用户注册 `recruitment-runner://` 协议。注册后，网页点击「一键唤起执行器」时，浏览器会弹确认框；选择允许后会打开本地执行器。

命令行启动方式仍然可用：

```bash
cd backend
.venv\Scripts\activate
python -m app.local_runner.main
```

默认监听：

```text
http://127.0.0.1:18765
```

## 网站端配合方式

1. 在「平台搜人」页创建任务
2. 点击「启动当前任务」或「创建并启动」
3. 前端会请求后端生成一次性 runner token
4. 浏览器向当前使用者电脑的 `127.0.0.1:18765/launch` 发送启动请求
5. runner 打开真实浏览器，登录平台、抓取候选人、上传日志与截图
6. 外联消息先回到网站审批，通过后由 runner 继续发送

## 上线给别人用时怎么跑

1. 服务器部署网站和后端 API。
2. 在服务器环境变量里配置 `PUBLIC_BACKEND_URL`，例如：

```env
PUBLIC_BACKEND_URL=https://api.yourdomain.com
```

3. 每个 HR 第一次使用平台搜人前，在网页「平台搜人」里下载 `recruitment-local-runner.zip`。
4. HR 在自己的电脑上解压 zip，双击 `start-local-runner.bat`。如果要网页一键唤起，再双击 `register-runner-protocol.bat`。
5. HR 登录线上网站，进入「平台搜人」，点击「检查」确认本地执行器已连接；或点击「一键唤起执行器」。
6. HR 创建任务并启动。网页会把一次性 token 和线上后端地址发给本机 runner。
7. 本机 runner 打开浏览器处理 BOSS 登录、验证码和搜索，然后把结果回传到线上后端。

注意：`127.0.0.1` 永远表示“打开网页的这台电脑”。所以线上部署后，别人要使用平台搜人，也必须在他自己的电脑启动 runner；服务器不需要也不应该直接登录 BOSS 抓取。

## 能不能真正一键？

浏览器为了安全，不能直接静默启动本机程序。最接近的一键方案有两种：

1. 下载双击版：用户第一次下载 `recruitment-local-runner.zip` 并解压，双击 `start-local-runner.bat`，之后网页点「启动任务」即可。
2. 协议唤起版：用户先运行 `register-runner-protocol.bat`，之后网页点「一键唤起执行器」，浏览器确认后启动。

如果要做到更产品化，可以把 runner 做成 Windows 安装包，安装时自动注册协议、创建桌面图标、开机自启。那样普通 HR 基本只需要安装一次。

当前后端提供：

```text
GET /api/sourcing/runner-package
```

登录用户可从该接口下载最小本地执行器包。包内只包含 runner 代码和启动脚本，不包含 AI 密钥、账号 Cookie 或任务 token。

## 当前协议

- `GET /api/sourcing/runner/tasks/{task_id}`: 拉取任务上下文
- `POST /api/sourcing/runner/tasks/{task_id}/status`: 更新任务状态
- `POST /api/sourcing/runner/tasks/{task_id}/logs`: 回传执行日志
- `POST /api/sourcing/runner/tasks/{task_id}/screenshots`: 回传截图
- `POST /api/sourcing/runner/tasks/{task_id}/candidates/batch`: 回传候选人批次
- `POST /api/sourcing/runner/tasks/{task_id}/outreach/{outreach_id}/delivery`: 回传发送结果

## 说明

- 当前 runner 走 Playwright 可见浏览器模式，适合处理登录、验证码和人工确认。
- 平台页面选择器使用通用启发式规则，若后续要提高 BOSS 直聘命中率，建议继续在 `app/local_runner/runtime.py` 里补平台专用选择器。
