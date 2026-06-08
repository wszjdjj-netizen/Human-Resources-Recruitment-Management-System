"""
面试管理模型

- Interview：一场面试（候选人 × 岗位 × 时间 × 链接）
- InterviewRecord：面试记录（转写全文、AI 总结、HR 协作笔记）

说明（demo）：
- 多 HR 协作：查询接口不按 user_id 过滤，所有 HR 可见
- 实时记录：MVP 不接入真实转写，由前端模拟；模型保留 transcript 字段
- AI 总结：复用 AIClient.chat_json，失败时回退 mock
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


# 面试状态
INTERVIEW_STATUS_SCHEDULED = "已预约"
INTERVIEW_STATUS_RUNNING = "进行中"
INTERVIEW_STATUS_TRANSCRIBING = "转写中"
INTERVIEW_STATUS_SUMMARIZED = "已总结"
INTERVIEW_STATUS_CANCELLED = "已取消"

INTERVIEW_STATUS_LIST = [
    INTERVIEW_STATUS_SCHEDULED,
    INTERVIEW_STATUS_RUNNING,
    INTERVIEW_STATUS_TRANSCRIBING,
    INTERVIEW_STATUS_SUMMARIZED,
    INTERVIEW_STATUS_CANCELLED,
]

INTERVIEW_STATUS_COLORS = {
    INTERVIEW_STATUS_SCHEDULED: "info",
    INTERVIEW_STATUS_RUNNING: "warning",
    INTERVIEW_STATUS_TRANSCRIBING: "primary",
    INTERVIEW_STATUS_SUMMARIZED: "success",
    INTERVIEW_STATUS_CANCELLED: "danger",
}

# 面试平台（仅展示，不做真实接入）
INTERVIEW_PLATFORMS = [
    {"value": "feishu", "label": "飞书会议", "color": "#3370ff"},
    {"value": "tencent", "label": "腾讯会议", "color": "#1aad19"},
    {"value": "zoom", "label": "Zoom", "color": "#2d8cff"},
    {"value": "dingtalk", "label": "钉钉会议", "color": "#1677ff"},
    {"value": "teams", "label": "Microsoft Teams", "color": "#5b5fc7"},
    {"value": "other", "label": "其他", "color": "#909399"},
]


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 创建人（仅用于追溯，不参与过滤）
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)

    # 面试标题（可选，默认「候选人姓名-岗位-时间」）
    title = Column(String(200), nullable=True)

    # 会议平台与链接
    platform = Column(String(30), nullable=False, default="feishu")
    meeting_url = Column(String(500), nullable=False)

    # 约定时间 & 时长
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=60)

    # 状态机
    status = Column(String(20), nullable=False, default=INTERVIEW_STATUS_SCHEDULED)

    # 时间戳
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class InterviewRecord(Base):
    __tablename__ = "interview_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    interview_id = Column(
        Integer, ForeignKey("interviews.id"), nullable=False, unique=True
    )

    # 完整转写（mock 流拼接后的全文；demo 里由前端一次性写入）
    transcript = Column(Text, nullable=True)

    # AI 总结（结构化 JSON 字符串），包含：
    #   overall: 综合评价
    #   highlights: 优势（list[str]）
    #   risks: 风险点（list[str]）
    #   recommendation: 推荐结论（强烈推荐 / 推荐 / 待定 / 不推荐）
    #   questions: 提问清单（list[str]）
    #   score: 综合评分 0-100
    summary_json = Column(Text, nullable=True)

    # HR 协作笔记（多行文本，约定格式：[时间][HR] 内容）
    notes = Column(Text, nullable=True)

    # 元信息
    summarized_by = Column(String(120), nullable=True, comment="生成总结的HR用户名")
    summarized_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
