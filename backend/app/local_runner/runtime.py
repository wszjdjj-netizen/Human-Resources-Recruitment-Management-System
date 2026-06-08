"""
本地 browser runner 运行时
"""
from __future__ import annotations

import base64
import threading
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx


OPEN_URLS = {
    "BOSS直聘": "https://www.zhipin.com/",
    "猎聘": "https://www.liepin.com/",
    "领英": "https://www.linkedin.com/",
    "脉脉": "https://maimai.cn/",
}

COOKIE_DOMAINS = {
    "BOSS直聘": ".zhipin.com",
    "猎聘": ".liepin.com",
    "领英": ".linkedin.com",
    "脉脉": ".maimai.cn",
}


@dataclass
class RunnerLaunchPayload:
    task_id: int
    backend_base_url: str
    runner_token: str
    session_id: str


class BackendClient:
    def __init__(self, payload: RunnerLaunchPayload):
        self.payload = payload
        self.client = httpx.Client(timeout=90.0)

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.payload.runner_token}",
            "X-Runner-Session-Id": self.payload.session_id,
        }

    def get_context(self) -> dict[str, Any]:
        res = self.client.get(
            f"{self.payload.backend_base_url}/api/sourcing/runner/tasks/{self.payload.task_id}",
            headers=self.headers,
        )
        res.raise_for_status()
        return res.json()

    def update_status(
        self,
        status: str,
        *,
        status_detail: str | None = None,
        pending_action: str | None = None,
        current_platform: str | None = None,
        runner_name: str | None = "Local Browser Runner",
        last_error: str | None = None,
        finished: bool = False,
    ):
        self.client.post(
            f"{self.payload.backend_base_url}/api/sourcing/runner/tasks/{self.payload.task_id}/status",
            headers=self.headers,
            json={
                "status": status,
                "status_detail": status_detail,
                "pending_action": pending_action,
                "current_platform": current_platform,
                "runner_name": runner_name,
                "last_error": last_error,
                "finished": finished,
            },
        ).raise_for_status()

    def log(self, message: str, *, level: str = "info", stage: str | None = None, detail: str | None = None):
        self.client.post(
            f"{self.payload.backend_base_url}/api/sourcing/runner/tasks/{self.payload.task_id}/logs",
            headers=self.headers,
            json={
                "level": level,
                "stage": stage,
                "message": message,
                "detail": detail,
            },
        ).raise_for_status()

    def upload_screenshot(
        self,
        image_bytes: bytes,
        *,
        mime_type: str = "image/png",
        stage: str | None = None,
        caption: str | None = None,
        source_url: str | None = None,
    ):
        self.client.post(
            f"{self.payload.backend_base_url}/api/sourcing/runner/tasks/{self.payload.task_id}/screenshots",
            headers=self.headers,
            json={
                "content_base64": base64.b64encode(image_bytes).decode("ascii"),
                "mime_type": mime_type,
                "stage": stage,
                "caption": caption,
                "source_url": source_url,
            },
        ).raise_for_status()

    def import_candidates(self, candidates: list[dict]) -> dict[str, Any]:
        res = self.client.post(
            f"{self.payload.backend_base_url}/api/sourcing/runner/tasks/{self.payload.task_id}/candidates/batch",
            headers=self.headers,
            json={"candidates": candidates},
        )
        res.raise_for_status()
        return res.json()

    def mark_delivery(
        self,
        outreach_id: int,
        *,
        status: str,
        detail: str | None = None,
        external_message_id: str | None = None,
        external_thread_id: str | None = None,
        payload: dict | None = None,
    ):
        self.client.post(
            f"{self.payload.backend_base_url}/api/sourcing/runner/tasks/{self.payload.task_id}/outreach/{outreach_id}/delivery",
            headers=self.headers,
            json={
                "status": status,
                "detail": detail,
                "external_message_id": external_message_id,
                "external_thread_id": external_thread_id,
                "payload": payload,
            },
        ).raise_for_status()


class GenericPlatformAdapter:
    def __init__(self, platform_name: str, platform_context: dict[str, Any]):
        self.platform_name = platform_name
        self.platform_context = platform_context

    @property
    def home_url(self) -> str:
        return OPEN_URLS.get(self.platform_name, "https://www.google.com/")

    @property
    def cookie_domain(self) -> str:
        return COOKIE_DOMAINS.get(self.platform_name, "")

    def execute(self, browser, backend: BackendClient, task_context: dict[str, Any]):
        page = browser.new_page()
        self._apply_cookies(page.context)
        try:
            page.goto(self.home_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as exc:
            backend.log(f"打开 {self.platform_name} 首页失败：{exc}，请检查网络或手动在浏览器中导航", level="error", stage="search")
            self._safe_screenshot(page, backend, stage="search", caption=f"{self.platform_name} 首页加载失败")
            raise
        page.wait_for_timeout(1500)
        if "about:blank" in (page.url or "") or "chrome-error://" in (page.url or ""):
            backend.log(f"页面停留在空白页（{page.url}），可能是 Cookie 失效或平台拦截了自动化访问", level="warning", stage="search")

        self._ensure_login(page, backend)
        backend.update_status("运行中", status_detail="登录完成，开始准备搜索候选人", current_platform=self.platform_name)
        self._safe_screenshot(page, backend, stage="search", caption=f"{self.platform_name} 搜索入口")

        self._navigate_to_search(page, backend, task_context)
        candidates = self._collect_candidate_profiles(page, backend, task_context)
        import_result = None
        if candidates:
            import_result = backend.import_candidates(candidates)
            backend.log(
                "候选人批次已回传",
                stage="import",
                detail=(
                    f"入库 {import_result['imported_count']} 人；重复 {import_result['duplicate_count']} 人；"
                    f"低于阈值 {import_result['filtered_count']} 人"
                ),
            )
        else:
            backend.log(
                "当前页面未提取到候选人卡片",
                level="warning",
                stage="scrape",
                detail="请在浏览器中切换到候选人搜索结果页后重新启动任务",
            )

        ready_to_finish = True
        if task_context["task"].get("auto_greeting") and import_result and import_result["imported_count"] > 0:
            ready_to_finish = self._wait_and_send_outreach(page, backend)

        if ready_to_finish:
            backend.update_status("完成", status_detail="本地执行器已结束本轮任务", current_platform=self.platform_name, finished=True)

    def _apply_cookies(self, context):
        raw_cookie = (self.platform_context or {}).get("credential") or ""
        if not raw_cookie or not self.cookie_domain:
            return
        cookies = []
        for item in raw_cookie.split(";"):
            if "=" not in item:
                continue
            name, value = item.split("=", 1)
            name = name.strip()
            value = value.strip()
            if not name:
                continue
            cookies.append({
                "name": name,
                "value": value,
                "domain": self.cookie_domain,
                "path": "/",
                "httpOnly": False,
                "secure": True,
            })
        if cookies:
            context.add_cookies(cookies)

    def _ensure_login(self, page, backend: BackendClient):
        if not self._looks_like_login(page) and not self._looks_like_captcha(page):
            return

        backend.update_status(
            "待登录",
            status_detail=f"请在弹出的浏览器中完成 {self.platform_name} 登录",
            pending_action="login",
            current_platform=self.platform_name,
        )
        backend.log("等待人工登录平台", stage="login")
        self._safe_screenshot(page, backend, stage="login", caption=f"{self.platform_name} 登录页")

        deadline = time.time() + 600
        last_status = "待登录"
        while time.time() < deadline:
            page.wait_for_timeout(3000)
            if self._looks_like_captcha(page):
                if last_status != "待验证码":
                    last_status = "待验证码"
                    backend.update_status(
                        "待验证码",
                        status_detail=f"检测到 {self.platform_name} 验证环节，请先完成人机验证",
                        pending_action="captcha",
                        current_platform=self.platform_name,
                    )
                    backend.log("检测到验证码或滑块验证", level="warning", stage="captcha")
                    self._safe_screenshot(page, backend, stage="captcha", caption=f"{self.platform_name} 验证页面")
                continue
            if not self._looks_like_login(page):
                backend.log("已完成平台登录", stage="login")
                return

        raise RuntimeError(f"{self.platform_name} 登录等待超时，请重新启动任务")

    def _navigate_to_search(self, page, backend: BackendClient, task_context: dict[str, Any]):
        position = task_context["position"]
        task = task_context["task"]
        query = task.get("keywords") or position.get("title") or ""
        preferred_url = position.get("platform_url")
        if preferred_url:
            try:
                page.goto(preferred_url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(1500)
                backend.log("已打开职位对应的平台链接", stage="search", detail=preferred_url)
                return
            except Exception as exc:
                backend.log("打开职位平台链接失败，将回退到首页搜索", level="warning", stage="search", detail=str(exc))

        selectors = [
            'input[placeholder*="搜索"]',
            'input[placeholder*="人才"]',
            'input[placeholder*="关键词"]',
            'input[type="search"]',
            'input[type="text"]',
        ]
        if not query:
            backend.log("任务未配置关键词，等待人工切换到候选人搜索页", level="warning", stage="search")
            page.wait_for_timeout(5000)
            return

        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if not locator.count():
                    continue
                locator.click(timeout=1500)
                locator.fill(query, timeout=2500)
                locator.press("Enter")
                page.wait_for_timeout(2500)
                backend.log("已尝试填写关键词并触发搜索", stage="search", detail=f"关键词：{query}")
                return
            except Exception:
                continue

        backend.log(
            "未找到稳定的搜索输入框，等待人工切换到候选人搜索结果页",
            level="warning",
            stage="search",
            detail=f"建议关键词：{query}",
        )
        page.wait_for_timeout(5000)

    def _collect_candidate_profiles(self, page, backend: BackendClient, task_context: dict[str, Any]) -> list[dict]:
        target_count = min(int(task_context["task"].get("target_count") or 10), 12)
        card_candidates = self._extract_visible_cards(page, target_count * 3)
        if not card_candidates:
            return []

        backend.log(
            "已从当前结果页发现候选人卡片",
            stage="scrape",
            detail=f"候选卡片数：{len(card_candidates)}",
        )
        self._safe_screenshot(page, backend, stage="scrape", caption=f"{self.platform_name} 结果页")

        results: list[dict] = []
        for item in card_candidates:
            if len(results) >= target_count:
                break
            profile_url = item.get("profile_url")
            raw_text = item.get("raw_text") or ""
            if profile_url:
                try:
                    detail_page = page.context.new_page()
                    detail_page.goto(profile_url, wait_until="domcontentloaded", timeout=45000)
                    detail_page.wait_for_timeout(1800)
                    raw_text = detail_page.locator("body").inner_text(timeout=3000)
                    if len(results) < 3:
                        self._safe_screenshot(
                            detail_page,
                            backend,
                            stage="profile",
                            caption=f"候选人详情：{item.get('name') or '未命名'}",
                            source_url=detail_page.url,
                        )
                    detail_page.close()
                except Exception as exc:
                    backend.log(
                        "打开候选人详情页失败，将使用列表页文本回传",
                        level="warning",
                        stage="profile",
                        detail=f"{item.get('profile_url')}: {exc}",
                    )

            if len(raw_text.strip()) < 20:
                continue

            results.append({
                "platform": self.platform_name,
                "external_id": item.get("external_id"),
                "profile_url": item.get("profile_url"),
                "name": item.get("name"),
                "current_company": item.get("current_company"),
                "current_position": item.get("current_position"),
                "raw_text": raw_text[:12000],
            })
        return results

    def _wait_and_send_outreach(self, page, backend: BackendClient) -> bool:
        backend.update_status(
            "待确认发送",
            status_detail="等待 HR 在网站端确认外联消息",
            pending_action="confirm_send",
            current_platform=self.platform_name,
        )
        backend.log("候选人已入库，开始等待外联审批", stage="outreach")

        deadline = time.time() + 600
        seen_outreach_ids: set[int] = set()
        while time.time() < deadline:
            context = backend.get_context()
            approved = context.get("pending_outreach") or []
            if approved:
                backend.update_status("运行中", status_detail="检测到已批准消息，开始发送", current_platform=self.platform_name)
                for item in approved:
                    if item["id"] in seen_outreach_ids:
                        continue
                    seen_outreach_ids.add(item["id"])
                    self._send_single_outreach(page, backend, item)
                return True
            page.wait_for_timeout(4000)

        backend.log("等待外联审批超时，本轮执行结束，后续可重新启动继续发送", level="warning", stage="outreach")
        backend.update_status(
            "待确认发送",
            status_detail="本轮执行结束，仍有消息待 HR 审批；审批后可重新启动继续发送",
            pending_action="confirm_send",
            current_platform=self.platform_name,
        )
        return False

    def _send_single_outreach(self, page, backend: BackendClient, outreach: dict[str, Any]):
        profile_url = outreach.get("profile_url")
        if not profile_url:
            backend.mark_delivery(outreach["id"], status="failed", detail="缺少候选人 profile_url，无法自动发送")
            return

        try:
            page.goto(profile_url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(1600)
            if self._looks_like_captcha(page):
                backend.update_status(
                    "待验证码",
                    status_detail="发送消息前触发了验证码，请先完成验证",
                    pending_action="captcha",
                    current_platform=self.platform_name,
                )
                self._safe_screenshot(page, backend, stage="captcha", caption="发送消息前验证码")
                self._wait_until_interactive(page, backend)

            self._click_first(page, [
                "button:has-text('立即沟通')",
                "button:has-text('打招呼')",
                "button:has-text('立即联系')",
                "button:has-text('聊一聊')",
                "[role='button']:has-text('立即沟通')",
            ])
            page.wait_for_timeout(1200)
            self._fill_message_box(page, outreach["message"])
            self._safe_screenshot(page, backend, stage="outreach", caption="发送消息前预览", source_url=page.url)
            self._click_first(page, [
                "button:has-text('发送')",
                "button:has-text('确认发送')",
                "button:has-text('立即发送')",
                "[role='button']:has-text('发送')",
            ])
            page.wait_for_timeout(1200)
            backend.mark_delivery(outreach["id"], status="sent", detail="本地执行器已点击发送")
            backend.log("已发送外联消息", stage="outreach", detail=f"outreach #{outreach['id']}")
        except Exception as exc:
            backend.mark_delivery(outreach["id"], status="failed", detail=str(exc))
            backend.log("发送外联消息失败", level="error", stage="outreach", detail=str(exc))

    def _wait_until_interactive(self, page, backend: BackendClient):
        deadline = time.time() + 300
        while time.time() < deadline:
            page.wait_for_timeout(3000)
            if not self._looks_like_captcha(page):
                backend.update_status("运行中", status_detail="验证码已完成，继续发送消息", current_platform=self.platform_name)
                return
        raise RuntimeError("验证码等待超时")

    def _click_first(self, page, selectors: list[str]):
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count():
                    locator.click(timeout=2500)
                    return True
            except Exception:
                continue
        return False

    def _fill_message_box(self, page, text: str):
        selectors = [
            "textarea",
            "[contenteditable='true']",
            "input[type='text']",
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if not locator.count():
                    continue
                locator.click(timeout=1500)
                try:
                    locator.fill(text, timeout=2500)
                except Exception:
                    locator.press("Control+A")
                    locator.type(text, delay=20)
                return
            except Exception:
                continue
        raise RuntimeError("未找到可填写的消息输入框")

    def _extract_visible_cards(self, page, limit: int) -> list[dict]:
        script = """
        (limit) => {
          const keywords = /(工程师|开发|产品|运营|销售|算法|Java|Python|前端|后端|测试|设计|经理|总监|本?科|硕士|经验|年)/i;
          const nodes = Array.from(document.querySelectorAll('a, article, li, section, div'));
          const records = [];
          const seen = new Set();
          for (const node of nodes) {
            const rect = node.getBoundingClientRect();
            if (rect.width < 120 || rect.height < 40) continue;
            if (rect.bottom < 0 || rect.top > window.innerHeight * 1.6) continue;
            const text = (node.innerText || '').replace(/\\s+/g, ' ').trim();
            if (text.length < 30 || text.length > 800) continue;
            const hrefNode = node.matches('a[href]') ? node : node.querySelector('a[href]');
            const href = hrefNode ? hrefNode.href : '';
            if (!keywords.test(text) && !/geek|candidate|profile|talent/i.test(href)) continue;
            const key = `${href}|${text.slice(0, 120)}`;
            if (seen.has(key)) continue;
            seen.add(key);
            const lines = text.split(/\\n+/).map(v => v.trim()).filter(Boolean);
            records.push({
              name: lines[0] || '平台候选人',
              current_position: lines[1] || lines[0] || '',
              current_company: lines[2] || '',
              raw_text: text,
              profile_url: href || null,
              external_id: href ? href.replace(/\\?.*$/, '').split('/').filter(Boolean).pop() : null,
            });
            if (records.length >= limit) break;
          }
          return records;
        }
        """
        return page.evaluate(script, limit)

    def _looks_like_login(self, page) -> bool:
        try:
            text = page.locator("body").inner_text(timeout=1200)[:2500]
        except Exception:
            text = ""
        url = page.url.lower()
        hints = ["登录", "扫码登录", "验证码登录", "手机号登录", "立即登录"]
        return "login" in url or any(item in text for item in hints)

    def _looks_like_captcha(self, page) -> bool:
        try:
            text = page.locator("body").inner_text(timeout=1200)[:2500]
        except Exception:
            text = ""
        url = page.url.lower()
        hints = ["验证码", "滑块", "安全验证", "请完成验证", "人机验证"]
        return "captcha" in url or any(item in text for item in hints)

    def _safe_screenshot(self, page, backend: BackendClient, *, stage: str, caption: str, source_url: str | None = None):
        try:
            url = page.url
            if not url or url == "about:blank" or "chrome-error://" in url:
                backend.log(f"跳过截图：当前页面为空或异常（{url}）", level="warning", stage=stage)
                return
            image = page.screenshot(full_page=True, type="png")
            backend.upload_screenshot(image, stage=stage, caption=caption, source_url=source_url or url)
        except Exception as exc:
            backend.log(f"截图失败：{exc}", level="warning", stage=stage)


class LocalRunnerJob:
    def __init__(self, payload: RunnerLaunchPayload):
        self.payload = payload
        self.thread: threading.Thread | None = None

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        backend = BackendClient(self.payload)
        try:
            backend.log("本地执行器已接收任务", stage="launch")
            backend.update_status("运行中", status_detail="正在启动浏览器", runner_name="Local Browser Runner")

            from playwright.sync_api import sync_playwright

            context_data = backend.get_context()
            platforms = context_data.get("task", {}).get("platforms") or []
            selected_platform = platforms[0] if platforms else "BOSS直聘"
            platform_context = next(
                (item for item in context_data.get("platforms", []) if item.get("platform") == selected_platform),
                {},
            )
            adapter = GenericPlatformAdapter(selected_platform, platform_context)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=False, slow_mo=80)
                try:
                    adapter.execute(browser, backend, context_data)
                finally:
                    browser.close()
        except Exception as exc:
            try:
                backend.log("本地执行器任务失败", level="error", stage="runner", detail=str(exc))
                backend.update_status("失败", status_detail="本地执行器执行失败", last_error=str(exc), finished=True)
            except Exception:
                pass
