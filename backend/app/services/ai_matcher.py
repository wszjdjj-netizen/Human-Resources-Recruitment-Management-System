"""
AI匹配打分服务
将候选人简历与岗位JD进行语义匹配，返回分数和分析
"""
import logging
from sqlalchemy.orm import Session

from app.services.ai_client import get_user_ai_client

logger = logging.getLogger(__name__)


MATCH_PROMPT = """你是一位资深招聘筛选专家，请根据以下岗位JD和候选人简历，评估两者的匹配度。

## 岗位信息
**职位名称**: {position_title}
**部门**: {department}
**工作地点**: {location}
**薪资范围**: {salary_range}

**岗位JD**:
{job_description}

**任职要求**:
{requirements}

## 候选人信息
**姓名**: {candidate_name}
**当前职位**: {current_position}
**当前公司**: {current_company}
**工作年限**: {work_years}年
**自我评价**: {self_evaluation}

**教育经历**:
{educations}

**工作经历**:
{experiences}

**技能**:
{skills}

## 打分维度（请逐一评估）
1. **工作年限匹配度** (0-20分)：候选人工作年限是否符合岗位要求
2. **技能匹配度** (0-25分)：候选人技能与岗位需求的重合度
3. **行业经验匹配度** (0-20分)：候选人过往行业/公司背景是否匹配
4. **学历匹配度** (0-15分)：候选人学历是否满足岗位要求
5. **综合匹配度** (0-20分)：整体印象、发展潜力、稳定性等综合评价

## 输出格式
请严格按照以下JSON格式输出：
{
  "score": 75,
  "analysis": "## 匹配度分析\\n\\n### 优势\\n1. 工作年限符合要求，具有5年Python经验...\\n2. 技能高度匹配，精通Python和FastAPI...\\n\\n### 不足\\n1. 缺少大数据相关项目经验...\\n2. ...\\n\\n### 综合建议\\n建议进入面试环节，重点考察..."
}

## 注意事项
- score 必须是0-100之间的整数
- analysis 使用Markdown格式，包含详细的匹配分析，便于HR阅读
- 分析要具体、有说服力，明确指出匹配点和差距点
- 不要过于严格，也不要过于宽松，给出客观公正的评价
"""


def build_educations_text(educations: list[dict]) -> str:
    """格式化教育经历为文本"""
    if not educations:
        return "无"
    lines = []
    for edu in educations:
        period = f"{edu.get('start_date', '?')} ~ {edu.get('end_date', '?')}"
        lines.append(f"- {period} | {edu.get('school', '')} | {edu.get('degree', '')} | {edu.get('major', '')}")
    return "\n".join(lines)


def build_experiences_text(experiences: list[dict]) -> str:
    """格式化工作经历为文本"""
    if not experiences:
        return "无"
    lines = []
    for exp in experiences:
        period = f"{exp.get('start_date', '?')} ~ {exp.get('end_date', '?')}"
        lines.append(f"- {period} | {exp.get('company', '')} | {exp.get('position', '')}")
        if exp.get('description'):
            lines.append(f"  职责: {exp['description'][:150]}")
    return "\n".join(lines)


def build_skills_text(skills: list[dict]) -> str:
    """格式化技能为文本"""
    if not skills:
        return "无"
    return "、".join([f"{s.get('skill_name', '')}({s.get('proficiency', '未知')})" for s in skills])


def match_candidate_to_position(
    position: dict,
    candidate: dict,
    educations: list[dict] = None,
    experiences: list[dict] = None,
    skills: list[dict] = None,
    db: Session | None = None,
    user_id: int | None = None,
) -> dict:
    """
    将候选人与岗位进行AI匹配打分

    Args:
        position: 职位信息（含title, department, location, salary_range, job_description, requirements）
        candidate: 候选人基本信息
        educations: 教育经历列表
        experiences: 工作经历列表
        skills: 技能列表

    Returns:
        {"score": int, "analysis": str}
    """
    if db is None or user_id is None:
        raise ValueError("当前账号尚未配置AI接口，请先进入「AI配置」页面保存自己的API Key")
    client = get_user_ai_client(db, user_id)

    prompt = MATCH_PROMPT.format(
        position_title=position.get("title", ""),
        department=position.get("department", ""),
        location=position.get("location", ""),
        salary_range=position.get("salary_range", "面议"),
        job_description=position.get("job_description", ""),
        requirements=position.get("requirements", "详见JD"),
        candidate_name=candidate.get("name", ""),
        current_position=candidate.get("current_position", "未知"),
        current_company=candidate.get("current_company", "未知"),
        work_years=candidate.get("work_years", 0) or 0,
        self_evaluation=candidate.get("self_evaluation", "无") or "无",
        educations=build_educations_text(educations or []),
        experiences=build_experiences_text(experiences or []),
        skills=build_skills_text(skills or []),
    )

    # 截断过长文本
    if len(prompt) > 12000:
        prompt = prompt[:12000]

    messages = [
        {"role": "system", "content": "你是一位资深招聘筛选专家。你要像招聘方一样评估候选人与岗位JD的匹配度，输出可解释、可入库、合法JSON。"},
        {"role": "user", "content": prompt}
    ]

    try:
        result = client.chat_json(messages, temperature=0.3)
        # 验证必有字段
        if "score" not in result or "analysis" not in result:
            raise ValueError("AI返回缺少必要字段")
        # 确保分数在0-100之间
        result["score"] = max(0, min(100, int(result["score"])))
        logger.info(f"匹配完成: {candidate.get('name')} -> {position.get('title')}, 分数: {result['score']}")
        return result
    except Exception as e:
        logger.error(f"匹配失败: {e}")
        fallback = fallback_match_candidate_to_position(position, candidate, educations or [], experiences or [], skills or [])
        fallback["analysis"] += f"\n\n> AI接口调用失败，已使用关键词兜底评分。原始错误：{e}"
        return fallback


def fallback_match_candidate_to_position(
    position: dict,
    candidate: dict,
    educations: list[dict],
    experiences: list[dict],
    skills: list[dict],
) -> dict:
    """AI不可用时的关键词兜底评分，避免筛选流程整批失败。"""
    import re

    jd_text = " ".join([
        position.get("title") or "",
        position.get("job_description") or "",
        position.get("requirements") or "",
    ]).lower()
    candidate_text = " ".join([
        candidate.get("current_position") or "",
        candidate.get("current_company") or "",
        candidate.get("self_evaluation") or "",
        " ".join(exp.get("description") or "" for exp in experiences),
        " ".join(skill.get("skill_name") or "" for skill in skills),
    ]).lower()
    tokens = [t for t in re.split(r"[\s,，、/;；。.\-+()（）]+", jd_text) if len(t) >= 2]
    unique_tokens = list(dict.fromkeys(tokens))[:40]
    hits = [t for t in unique_tokens if t and t in candidate_text]
    skill_hits = [s.get("skill_name") for s in skills if s.get("skill_name") and s.get("skill_name").lower() in jd_text]
    years = candidate.get("work_years") or 0
    score = min(88, 35 + len(hits) * 3 + len(skill_hits) * 6 + min(years, 8) * 2)
    score = max(20, score)
    return {
        "score": int(score),
        "analysis": (
            "## 兜底匹配分析\n\n"
            f"候选人与JD命中的关键词：{', '.join(hits[:12]) or '暂无明显关键词'}。\n\n"
            f"命中的技能标签：{', '.join(skill_hits[:8]) or '暂无明显技能标签'}。\n\n"
            "建议在AI接口恢复后重新执行匹配，以获得更完整的招聘专家分析。"
        )
    }
