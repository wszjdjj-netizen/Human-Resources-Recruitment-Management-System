"""
工作流匹配自定义角色模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class WorkflowRole(Base):
    __tablename__ = "workflow_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # 角色基本信息
    name = Column(String(100), nullable=False, comment="角色名称")
    description = Column(String(300), nullable=True, comment="角色描述")
    # AI配置
    system_prompt = Column(Text, nullable=False, comment="系统提示词/人设描述")
    # 评分维度（JSON数组: [{name, max_score, desc}]）
    eval_dimensions_json = Column(
        Text, nullable=False,
        default='[{"name":"综合匹配度", "max_score": 100, "desc":"综合评估候选人与岗位的匹配程度"}]',
        comment="评分维度配置JSON",
    )
    # 元数据
    is_builtin = Column(Integer, nullable=False, default=0, comment="是否为内置预设(0=自定义,1=内置)")
    builtin_key = Column(String(50), nullable=True, comment="对应内置预设的key")
    sort_order = Column(Integer, nullable=False, default=0, comment="排序序号")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def eval_dimensions(self) -> list[dict]:
        """解析评分维度JSON"""
        import json
        try:
            return json.loads(self.eval_dimensions_json) if self.eval_dimensions_json else []
        except (json.JSONDecodeError, TypeError):
            return [{"name": "综合匹配度", "max_score": 100, "desc": ""}]

    @eval_dimensions.setter
    def eval_dimensions(self, value: list[dict]):
        """设置评分维度JSON"""
        import json
        self.eval_dimensions_json = json.dumps(value, ensure_ascii=False)
