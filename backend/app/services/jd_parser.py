"""
JD智能解析服务
支持粘贴JD文本或招聘职位URL，AI自动提取结构化职位信息
URL抓取策略：先尝试静态提取（JSON-LD/JS状态/meta），失败后用Playwright渲染
"""
import re
import json
import logging
import httpx
from sqlalchemy.orm import Session
from urllib.parse import urljoin

from app.services.ai_client import get_user_ai_client
from app.config import get_settings
from app.security import normalize_public_http_url

logger = logging.getLogger(__name__)

MAX_FETCH_REDIRECTS = 5

JD_PARSE_PROMPT = """你是一位专业的招聘专家，请从以下招聘信息中提取结构化的职位数据。请以JSON格式返回。

## 提取规则
1. title: 职位名称
2. department: 所属部门（如无法判断，根据职位内容合理推断）
3. location: 工作地点（城市名称）
4. salary_range: 薪资范围（如原始信息中有则提取，否则为null）
5. job_description: 完整的岗位职责描述（保留原文中的结构化信息）
6. requirements: 任职要求（提取学历、经验、技能等硬性要求，分条列出）

## 输出格式（严格JSON）
{
  "title": "高级Python开发工程师",
  "department": "技术部",
  "location": "北京",
  "salary_range": "25K-40K",
  "job_description": "1. 负责公司核心业务系统的架构设计与开发\\n2. 参与技术方案评审和代码review\\n3. ...",
  "requirements": "1. 本科及以上学历，计算机相关专业\\n2. 3年以上Python后端开发经验\\n3. 精通FastAPI/Django等主流框架\\n4. ..."
}

## 招聘信息原文
{jd_text}

请直接输出JSON，不要输出任何其他内容。"""


def fetch_url_content(url: str) -> str:
    """
    获取URL的文本内容
    优先从HTML的meta标签、JSON-LD、JS初始状态中提取结构化数据，
    如果都提取不到足够的文本，再做HTML标签剥离
    """
    settings = get_settings()
    try:
        url = normalize_public_http_url(
            url,
            allow_private=settings.allow_private_network_urls,
            require_resolvable=True,
        )
    except ValueError as exc:
        raise ValueError(str(exc))

    try:
        client = httpx.Client(timeout=30.0, follow_redirects=False, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        response = _get_with_validated_redirects(
            client,
            url,
            allow_private=settings.allow_private_network_urls,
        )
        response.raise_for_status()
        html = response.text

        # ====== 策略1：提取 JSON-LD 结构化数据 ======
        jsonld_matches = re.findall(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL | re.IGNORECASE
        )
        jsonld_texts = []
        for match in jsonld_matches:
            try:
                data = json.loads(match.strip())
                # 提取JobPosting类型的结构化数据
                if isinstance(data, dict):
                    parts = []
                    if data.get('title'):
                        parts.append(f"职位: {data['title']}")
                    if data.get('description'):
                        parts.append(data['description'])
                    if data.get('hiringOrganization'):
                        org = data['hiringOrganization']
                        if isinstance(org, dict) and org.get('name'):
                            parts.append(f"公司: {org['name']}")
                    if data.get('jobLocation'):
                        loc = data['jobLocation']
                        if isinstance(loc, dict) and loc.get('address'):
                            addr = loc['address']
                            if isinstance(addr, dict):
                                parts.append(f"地点: {addr.get('addressLocality', '')}")
                    if data.get('baseSalary'):
                        sal = data['baseSalary']
                        if isinstance(sal, dict):
                            parts.append(f"薪资: {sal.get('value', '')} {sal.get('currency', '')}")
                    if parts:
                        jsonld_texts.append('\n'.join(parts))
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                            parts = []
                            if item.get('title'):
                                parts.append(f"职位: {item['title']}")
                            if item.get('description'):
                                parts.append(item['description'])
                            if parts:
                                jsonld_texts.append('\n'.join(parts))
            except json.JSONDecodeError:
                pass

        if jsonld_texts:
            combined = '\n\n'.join(jsonld_texts)
            logger.info(f"从JSON-LD提取到 {len(combined)} 字符")
            return combined[:10000]

        # ====== 策略2：提取 JS 初始化状态中的职位数据 ======
        # 常见模式: window.__INITIAL_STATE__ = { ... }
        state_patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'window\.__NUXT__\s*=\s*({.+?});',
            r'window\.__NEXT_DATA__\s*=\s*({.+?});',
            r'window\._DATA_\s*=\s*({.+?});',
        ]
        for pattern in state_patterns:
            state_match = re.search(pattern, html, re.DOTALL)
            if state_match:
                try:
                    state_data = json.loads(state_match.group(1))
                    # 递归搜索其中可能的职位信息
                    job_parts = _extract_job_info_from_json(state_data)
                    if job_parts:
                        combined = '\n'.join(job_parts)
                        logger.info(f"从JS初始状态中提取到 {len(combined)} 字符")
                        return combined[:10000]
                except json.JSONDecodeError:
                    pass

        # ====== 策略3：提取 meta 标签 + title ======
        meta_texts = []

        # 提取 og:title / og:description
        for prop in ['og:title', 'og:description', 'description']:
            for attr in ['property', 'name']:
                meta_match = re.search(
                    rf'<meta[^>]+{attr}=["\']{prop}["\'][^>]+content=["\']([^"\']+)["\']',
                    html, re.IGNORECASE
                )
                if meta_match:
                    meta_texts.append(meta_match.group(1))
                    break

        # 提取 <title>
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            # 清理常见的标题后缀
            title = re.sub(r'\s*[-–|]\s*(Boss直聘|猎聘|领英|智联招聘|前程无忧).*$', '', title)
            if title and title not in meta_texts:
                meta_texts.insert(0, f"职位: {title}")

        if meta_texts:
            combined = '\n'.join(meta_texts)
            logger.info(f"从meta标签提取到 {len(combined)} 字符")

        # ====== 策略4：提取 body 纯文本 ======
        # 去除 script 和 style
        clean_html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        clean_html = re.sub(r'<style[^>]*>.*?</style>', '', clean_html, flags=re.DOTALL | re.IGNORECASE)
        clean_html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', clean_html, flags=re.DOTALL | re.IGNORECASE)

        # 提取 <body> 内容（如果有）
        body_match = re.search(r'<body[^>]*>(.*?)</body>', clean_html, re.DOTALL | re.IGNORECASE)
        target = body_match.group(1) if body_match else clean_html

        # 提取所有可见文本
        text = re.sub(r'<[^>]+>', '\n', target)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        clean_text = '\n'.join(lines)

        # 去重相邻重复行
        deduped = []
        for line in clean_text.split('\n'):
            if not deduped or deduped[-1] != line:
                deduped.append(line)
        body_text = '\n'.join(deduped)

        # 合并 meta 内容和 body 内容
        if meta_texts:
            body_text = '\n'.join(meta_texts) + '\n\n---\n\n' + body_text

        # 清理
        body_text = re.sub(r'\n{3,}', '\n\n', body_text).strip()

        if len(body_text) > 10000:
            body_text = body_text[:10000]

        logger.info(f"最终提取到 {len(body_text)} 字符")
        return body_text

    except httpx.HTTPError as e:
        raise ValueError(f"获取URL内容失败：{e}")
    except Exception as e:
        raise ValueError(f"URL解析失败：{e}")


def _get_with_validated_redirects(client: httpx.Client, url: str, *, allow_private: bool) -> httpx.Response:
    current_url = url
    for _ in range(MAX_FETCH_REDIRECTS + 1):
        response = client.get(current_url)
        if not response.is_redirect:
            return response
        location = response.headers.get("location")
        if not location:
            return response
        next_url = urljoin(str(response.url), location)
        current_url = normalize_public_http_url(
            next_url,
            allow_private=allow_private,
            require_resolvable=True,
        )
    raise ValueError("URL重定向次数过多")


def _extract_job_info_from_json(data, depth=0, max_depth=4) -> list[str]:
    """递归搜索JSON对象中的职位相关信息"""
    if depth > max_depth or data is None:
        return []

    parts = []

    if isinstance(data, dict):
        # 检查是否包含职位相关的key
        title_keys = {'title', 'jobTitle', 'jobName', 'positionName', 'name', 'job_title', 'position_name'}
        desc_keys = {'description', 'jobDescription', 'jobDesc', 'detail', 'job_detail', 'responsibility', 'requirements'}
        company_keys = {'company', 'companyName', 'hiringOrganization', 'brandName'}
        location_keys = {'location', 'city', 'workCity', 'address'}
        salary_keys = {'salary', 'salaryRange', 'compensation', 'pay'}

        extracted_title = None
        extracted_desc = None

        for key, value in data.items():
            if key in title_keys and isinstance(value, str) and len(value) > 1:
                extracted_title = f"职位: {value}"
            if key in desc_keys and isinstance(value, str) and len(value) > 20:
                extracted_desc = value
            if key in company_keys and isinstance(value, str) and len(value) > 1:
                parts.append(f"公司: {value}")
            if key in location_keys and isinstance(value, str) and len(value) > 1:
                parts.append(f"地点: {value}")
            if key in salary_keys and isinstance(value, (str, int)):
                parts.append(f"薪资: {value}")

        if extracted_title:
            parts.insert(0, extracted_title)
        if extracted_desc:
            parts.append(extracted_desc)

        # 继续递归搜索
        if not extracted_desc:  # 还没找到描述才继续搜
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    sub_parts = _extract_job_info_from_json(value, depth + 1, max_depth)
                    if sub_parts and not parts:
                        parts = sub_parts

    elif isinstance(data, list):
        for item in data[:10]:  # 限制搜索范围
            sub_parts = _extract_job_info_from_json(item, depth + 1, max_depth)
            if sub_parts:
                parts.extend(sub_parts)
                if len(parts) > 5:
                    break

    return parts


def _fetch_with_playwright(url: str) -> str:
    """
    使用Playwright无头浏览器渲染JS动态页面，提取完整文本
    """
    settings = get_settings()
    try:
        url = normalize_public_http_url(
            url,
            allow_private=settings.allow_private_network_urls,
            require_resolvable=True,
        )
    except ValueError as exc:
        raise ValueError(str(exc))

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ValueError("Playwright未安装，无法抓取动态页面。请直接粘贴JD文本。")

    logger.info(f"Playwright渲染中: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN"
        )
        page = context.new_page()

        def block_private_requests(route):
            request_url = route.request.url
            if request_url.startswith(("data:", "blob:", "about:")):
                route.continue_()
                return
            try:
                normalize_public_http_url(
                    request_url,
                    allow_private=settings.allow_private_network_urls,
                    require_resolvable=True,
                )
            except ValueError:
                route.abort()
                return
            route.continue_()

        page.route("**/*", block_private_requests)
        try:
            # 加载页面，等待网络空闲
            page.goto(url, wait_until="networkidle", timeout=30000)
            # 额外等待确保JS渲染完成
            page.wait_for_timeout(2000)

            # 获取页面完整文本
            body_text = page.inner_text("body")

            # 同时尝试提取 meta 信息
            title = page.title() or ""
            meta_desc = ""
            try:
                meta_desc = page.locator('meta[name="description"]').get_attribute("content") or ""
            except Exception:
                meta_desc = ""

            # 合并标题+描述+正文
            parts = []
            if title:
                parts.append(f"职位: {title}")
            if meta_desc:
                parts.append(meta_desc)
            parts.append(body_text)

            text = "\n".join(parts)
            # 去重相邻重复行
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            deduped = []
            for line in lines:
                if not deduped or deduped[-1] != line:
                    deduped.append(line)

            result = "\n".join(deduped)
            logger.info(f"Playwright提取到 {len(result)} 字符")
            return result[:15000]

        except Exception as e:
            logger.error(f"Playwright渲染失败: {e}")
            raise ValueError(f"页面加载失败：{e}")
        finally:
            browser.close()


def parse_jd(text: str = None, url: str = None, db: Session | None = None, user_id: int | None = None) -> dict:
    """
    解析JD文本或URL，提取结构化职位信息

    Args:
        text: 粘贴的JD文本
        url: 招聘职位链接

    Returns:
        结构化的职位信息字典：{title, department, location, salary_range, job_description, requirements}
    """
    # 确定输入源
    if url:
        logger.info(f"从URL获取JD: {url}")
        # 先尝试静态提取
        jd_text = fetch_url_content(url)

        # 内容不够 → 上Playwright渲染
        if len(jd_text) < 100:
            logger.info("静态提取内容不足，尝试Playwright渲染...")
            try:
                jd_text = _fetch_with_playwright(url)
            except Exception as pw_err:
                logger.warning(f"Playwright也失败了: {pw_err}")
                raise ValueError(
                    "无法自动获取该页面内容。页面可能是需要登录才能查看，"
                    "或使用了反爬机制。\n\n"
                    "解决方案：在职位页面手动全选复制JD全文，"
                    "切换到「粘贴JD文本」标签页粘贴即可。"
                )
    elif text:
        jd_text = text.strip()
    else:
        raise ValueError("请提供JD文本或职位链接")

    if len(jd_text) < 20:
        raise ValueError("JD内容过短，请提供完整的职位描述")

    # 调用AI解析
    if db is None or user_id is None:
        raise ValueError("当前账号尚未配置AI接口，请先进入「AI配置」页面保存自己的API Key")
    client = get_user_ai_client(db, user_id)
    prompt = JD_PARSE_PROMPT.replace("{jd_text}", jd_text[:8000])  # 限制长度

    messages = [
        {"role": "system", "content": "你是一位招聘数据专家，请精确提取JD中的结构化信息，严格按JSON输出。"},
        {"role": "user", "content": prompt}
    ]

    try:
        result = client.chat_json(messages, temperature=0.2)
        # 确保必填字段存在
        result.setdefault("title", "未命名职位")
        result.setdefault("department", "未分类")
        result.setdefault("location", "待定")
        result.setdefault("salary_range", None)
        result.setdefault("job_description", jd_text[:2000])
        result.setdefault("requirements", "")
        logger.info(f"JD解析成功: {result.get('title')}")
        return result
    except Exception as e:
        logger.error(f"JD解析失败: {e}")
        raise ValueError(f"AI解析JD失败：{e}")
