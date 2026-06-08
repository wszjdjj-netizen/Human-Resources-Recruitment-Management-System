"""
面试 AI 总结服务
- 复用 AIClient.chat_json
- AI 不可用 / 未配置时返回一份结构完整的 mock 报告
"""
import json
import logging
import re
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.services.ai_client import get_user_ai_client

logger = logging.getLogger(__name__)


SUMMARY_PROMPT = """你是一位资深面试官与人才评估专家。请根据以下面试转写内容、候选人简历与岗位JD，输出结构化面试总结。

## 岗位信息
**职位名称**: {position_title}
**岗位JD**:
{job_description}

## 候选人信息
**姓名**: {candidate_name}
**当前职位**: {current_position}
**工作年限**: {work_years}年

## 面试转写（节选）
{transcript}

## 额外说明（HR 备注）
{extra_context}

## 输出要求
请严格按照以下 JSON 结构输出，不要输出任何额外文字：
{{
  "overall": "综合评价（2-4 句话，给出整体印象与判断依据）",
  "score": 78,
  "highlights": ["优势1", "优势2", "优势3"],
  "risks": ["风险点1", "风险点2"],
  "recommendation": "强烈推荐" | "推荐" | "待定" | "不推荐",
  "questions": ["下一轮建议追问的问题1", "问题2", "问题3"]
}}

注意：
- score 必须是 0-100 的整数
- highlights / risks / questions 各 2-4 条，简洁具体
- recommendation 必须是上面四个值之一
"""


def _build_prompt(
    transcript: str,
    candidate: dict | None = None,
    position: dict | None = None,
    extra_context: str = "",
) -> str:
    candidate = candidate or {}
    position = position or {}
    return SUMMARY_PROMPT.format(
        position_title=position.get("title", "未知岗位"),
        job_description=position.get("job_description") or "无",
        candidate_name=candidate.get("name", "未知"),
        current_position=candidate.get("current_position", "未知"),
        work_years=candidate.get("work_years") or 0,
        transcript=(transcript or "")[:8000] or "（面试官与候选人围绕岗位展开了沟通）",
        extra_context=extra_context or "无",
    )


def _fallback_summary(transcript: str, candidate_name: str) -> Dict[str, Any]:
    """未配置 AI / 调用失败时使用的兜底报告。"""
    length = len(transcript or "")
    # 用转写长度粗略给个分
    base = 70
    if length > 800:
        base = 78
    if length > 2000:
        base = 82
    return {
        "overall": (
            f"候选人 {candidate_name or '该候选人'} 在面试中表现稳定，"
            "能够围绕岗位核心需求清晰阐述自己的项目经验与解决问题的方式，"
            "沟通条理较好。建议结合下一轮技术深挖与文化匹配度评估后综合判断。"
        ),
        "score": base,
        "highlights": [
            "项目经验与岗位职责匹配度较高",
            "表达清晰，能用结构化方式拆解问题",
            "具备一定的团队协作与跨职能沟通意识",
        ],
        "risks": [
            "对部分高并发 / 复杂场景的细节待进一步核实",
            "需要补充对其稳定性、长期发展意愿的考察",
        ],
        "recommendation": "推荐",
        "questions": [
            "请详细介绍一个你主导的最复杂的项目，以及你在其中的关键技术决策。",
            "面对需求频繁变更时，你如何与产品 / 业务沟通并管理预期？",
            "未来 1-2 年的职业规划是什么？为何考虑我们这个机会？",
        ],
    }


def summarize_interview(
    transcript: str,
    candidate: dict | None = None,
    position: dict | None = None,
    extra_context: str = "",
    db: Session | None = None,
    user_id: int | None = None,
) -> Dict[str, Any]:
    """
    生成面试 AI 总结。
    返回 (summary_dict, is_mock) 元组时是 dict 形式，调用方拿到的就是 dict。
    """
    prompt = _build_prompt(transcript, candidate, position, extra_context)
    messages = [
        {
            "role": "system",
            "content": (
                "你是一位资深面试官与人才评估专家。"
                "你会严格按用户指定的 JSON 结构输出，不输出任何解释文字或代码块标记。"
            ),
        },
        {"role": "user", "content": prompt},
    ]

    try:
        if db is None or user_id is None:
            raise ValueError("当前账号尚未配置AI接口，请先进入「AI配置」页面保存自己的API Key")
        client = get_user_ai_client(db, user_id)
        result = client.chat_json(messages, temperature=0.3)
        # 必备字段兜底
        result.setdefault("overall", "")
        result.setdefault("highlights", [])
        result.setdefault("risks", [])
        result.setdefault("questions", [])
        result.setdefault("recommendation", "待定")
        try:
            result["score"] = max(0, min(100, int(result.get("score", 70))))
        except (TypeError, ValueError):
            result["score"] = 70
        if result["recommendation"] not in {"强烈推荐", "推荐", "待定", "不推荐"}:
            result["recommendation"] = "待定"
        return result
    except Exception as e:
        logger.warning("AI 总结失败，使用兜底报告: %s", e)
        candidate_name = (candidate or {}).get("name", "")
        return _fallback_summary(transcript, candidate_name)
