"""
AI简历解析服务
将简历原始文本解析为结构化的候选人信息
"""
import logging
from sqlalchemy.orm import Session

from app.services.ai_client import get_user_ai_client

logger = logging.getLogger(__name__)


# AI简历解析提示词
PARSE_RESUME_PROMPT = """你是一位资深招聘筛选专家和简历结构化解析助手，请从以下简历文本中提取关键信息，并以JSON格式返回。

## 提取规则
1. 姓名：提取候选人的中文或英文姓名
2. 电话：中国大陆手机号码（11位）或带区号的座机
3. 邮箱：电子邮箱地址
4. 性别：根据简历中的称呼推断（男/女），无法判断则为null
5. 年龄：根据出生日期或简历中提及的年龄计算，无法判断则为null
6. 当前公司：候选人目前就职的公司名称
7. 当前职位：候选人目前的职位名称
8. 工作年限：总工作年限（整数），无法判断则为null
9. 自我评价：候选人简历中的自我评价或个人总结部分（不超过200字）
10. 教育经历：数组，每项包含 school(学校), degree(学历如本科/硕士/博士/大专), major(专业), start_date(起始时间如2018-09), end_date(结束时间如2022-06)
11. 工作经历：数组，每项包含 company(公司), position(职位), start_date(起始), end_date(结束), description(工作内容描述，精简到100字以内)
12. 技能：数组，每项包含 skill_name(技能名称), proficiency(熟练程度：了解/熟练/精通)

## 输出格式
请严格按照以下JSON格式输出，不要输出任何其他内容：
{
  "name": "张三",
  "phone": "13800138000",
  "email": "zhangsan@example.com",
  "gender": "男",
  "age": 28,
  "current_company": "某科技有限公司",
  "current_position": "高级Python工程师",
  "work_years": 5,
  "self_evaluation": "拥有5年Python后端开发经验...",
  "educations": [
    {"school": "清华大学", "degree": "硕士", "major": "计算机科学", "start_date": "2018-09", "end_date": "2021-06"}
  ],
  "experiences": [
    {"company": "某科技公司", "position": "Python工程师", "start_date": "2021-07", "end_date": "至今", "description": "负责后端API开发与维护"}
  ],
  "skills": [
    {"skill_name": "Python", "proficiency": "精通"},
    {"skill_name": "FastAPI", "proficiency": "熟练"}
  ]
}

## 注意事项
- 如果某个字段无法从简历中提取，设置为null（字符串字段）或空数组（数组字段）
- 电话号码只提取第一个有效的手机号码
- 工作经历按时间倒序排列（最近的在前面）
- 保持数据准确，不要编造信息
- 对于教育/工作经历中的必填字段，如果原文没有明确写出，请用"未知"兜底，避免返回null
- 技能名称不能为空；无法判断熟练度时 proficiency 可为null

## 简历文本
{resume_text}
"""


def parse_resume(raw_text: str, extra_prompt: str = None, db: Session | None = None, user_id: int | None = None) -> dict:
    """
    使用AI解析简历文本为结构化数据

    Args:
        raw_text: 简历原始文本（从PDF/Word提取）
        extra_prompt: 额外的解析提示词（如候选人画像、特定技能要求等）。
                      为None时使用纯通用解析模式。

    Returns:
        结构化的候选人信息字典
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("简历文本为空，无法解析")

    if db is None or user_id is None:
        raise ValueError("当前账号尚未配置AI接口，请先进入「AI配置」页面保存自己的API Key")
    client = get_user_ai_client(db, user_id)

    # 截断过长的文本（防止token超限）
    max_chars = 8000
    text_to_parse = raw_text[:max_chars] if len(raw_text) > max_chars else raw_text

    prompt = PARSE_RESUME_PROMPT.replace("{resume_text}", text_to_parse)

    # 添加额外的定制提示词
    if extra_prompt and extra_prompt.strip():
        custom_instruction = f"""

## 额外解析要求（针对特定岗位的候选人画像）
以下是对该岗位候选人的特别关注点，请在解析时重点识别这些信息：
{extra_prompt.strip()}

请在上方JSON输出中额外增加一个字段 "custom_notes"（字符串），总结候选人在以上特别关注点方面的匹配情况。"""
        prompt += custom_instruction

    messages = [
        {"role": "system", "content": "你是一位资深招聘筛选专家，擅长从中文/英文简历中提取稳定、可入库的结构化信息。你必须严格输出合法JSON。"},
        {"role": "user", "content": prompt}
    ]

    try:
        result = client.chat_json(messages, temperature=0.2)
        logger.info(f"简历解析成功: {result.get('name', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"简历解析失败: {e}")
        raise ValueError(f"AI简历解析失败: {e}")
