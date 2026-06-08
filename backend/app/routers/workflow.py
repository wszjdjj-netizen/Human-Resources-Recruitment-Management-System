"""
工作流模式匹配路由（独立于平台搜人）

专门用于AI角色设定下的简历与JD匹配打分，与平台搜人功能完全隔离，
确保两者并发运行时不会互相干扰。

支持：
- 4种内置角色预设（只读，不可删除）
- 用户自定义角色（可新建、编辑、删除）
- 匹配时可选用内置或自定义角色
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.jwt_middleware import get_current_user
from app.models.candidate import Candidate
from app.models.education import CandidateEducation
from app.models.experience import CandidateExperience
from app.models.match_result import MatchResult
from app.models.position import Position
from app.models.skill import CandidateSkill
from app.models.user import User
from app.models.workflow_role import WorkflowRole as WorkflowRoleModel
from app.services.ai_matcher import (
    build_educations_text,
    build_experiences_text,
    build_skills_text,
    match_candidate_to_position,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow", tags=["工作流匹配"])

# ==================== 内置角色预设（只读） ====================

BUILTIN_ROLE_PRESETS = {
    "recruiter": {
        "name": "资深招聘专家",
        "description": "从招聘方视角评估候选人，关注综合能力、团队协作和岗位匹配度",
        "system_prompt": "你是一位拥有15年经验的资深招聘专家，曾服务过多家500强企业。你擅长从多维度评估候选人与岗位的匹配度，能够准确识别候选人的优势和潜在风险。",
        "eval_dimensions": [
            {"name": "工作年限匹配度", "max_score": 20, "desc": "候选人工作年限是否符合岗位要求"},
            {"name": "技能匹配度", "max_score": 25, "desc": "候选人技能与岗位需求的重合度"},
            {"name": "行业经验匹配度", "max_score": 20, "desc": "候选人过往行业/公司背景是否匹配"},
            {"name": "学历匹配度", "max_score": 15, "desc": "候选人学历是否满足岗位要求"},
            {"name": "综合匹配度", "max_score": 20, "desc": "整体印象、发展潜力、稳定性等综合评价"},
        ],
    },
    "tech_interviewer": {
        "name": "技术面试官",
        "description": "从技术视角深入评估候选人的专业能力和项目经验",
        "system_prompt": "你是一位资深技术面试官，在软件工程领域有超过10年的经验。你擅长从技术深度、架构思维、代码质量等方面评估候选人。",
        "eval_dimensions": [
            {"name": "核心技术栈匹配度", "max_score": 30, "desc": "核心技能与岗位技术要求的匹配程度"},
            {"name": "项目经验相关度", "max_score": 25, "desc": "过往项目经验与目标岗位的相关性"},
            {"name": "技术深度", "max_score": 20, "desc": "在关键技术领域的深度理解"},
            {"name": "架构与设计能力", "max_score": 15, "desc": "系统设计、架构思维能力"},
            {"name": "成长潜力", "max_score": 10, "desc": "学习能力、技术热情和发展潜力"},
        ],
    },
    "hr_bp": {
        "name": "HRBP (业务合作伙伴)",
        "description": "从组织发展和人才培养角度评估候选人的文化契合度和长期价值",
        "system_prompt": "你是一位专业的HRBP，擅长从组织发展角度评估人才。你不仅关注硬性技能，更重视候选人的软实力、价值观契合度和长期发展潜力。",
        "eval_dimensions": [
            {"name": "文化契合度", "max_score": 25, "desc": "候选人价值观与企业文化的匹配程度"},
            {"name": "软技能", "max_score": 25, "desc": "沟通能力、领导力、协作能力等"},
            {"name": "职业稳定性", "max_score": 15, "desc": "职业路径连贯性和稳定性预期"},
            {"name": "学习适应力", "max_score": 15, "desc": "快速学习和适应变化的能力"},
            {"name": "岗位硬性条件", "max_score": 20, "desc": "学历、年限、核心技能等基本门槛"},
        ],
    },
    "hiring_manager": {
        "name": "用人部门经理",
        "description": "从实际用人需求出发，聚焦于即战力和团队融入",
        "system_prompt": "你是一位一线用人经理，你需要找到能快速上手、为团队创造价值的人。你务实直接，看重实际产出能力和团队配合。",
        "eval_dimensions": [
            {"name": "即战力评估", "max_score": 30, "desc": "入职后能快速产出价值的能力"},
            {"name": "团队能力互补", "max_score": 20, "desc": "能否补足当前团队的能力缺口"},
            {"name": "业务理解力", "max_score": 20, "desc": "对业务领域和产品逻辑的理解程度"},
            {"name": "沟通效率", "max_score": 15, "desc": "信息传递效率和跨部门协作能力"},
            {"name": "成本性价比", "max_score": 15, "desc": "综合考虑薪资期望和能力产出的性价比"},
        ],
    },
}


# ==================== 数据模型 ====================

class DimensionDef(BaseModel):
    """评分维度定义"""
    name: str = Field(..., min_length=1, max_length=50)
    max_score: int = Field(..., ge=1, le=100)
    desc: str = Field("", max_length=200)


class RoleCreateRequest(BaseModel):
    """创建自定义角色"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    system_prompt: str = Field(..., min_length=10)
    eval_dimensions: list[DimensionDef] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="至少1个评分维度，最多10个",
    )


class RoleUpdateRequest(BaseModel):
    """更新自定义角色"""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    system_prompt: str | None = Field(None, min_length=10)
    eval_dimensions: list[DimensionDef] | None = Field(None, min_length=1, max_length=10)


class WorkflowRoleConfig(BaseModel):
    """工作流匹配时的角色选择配置"""
    # 三选一：使用内置角色 / 使用自定义角色ID / 直接传入完整配置
    builtin_role_type: str | None = Field(
        None,
        description="使用内置预设角色: recruiter/tech_interviewer/hr_bp/hiring_manager"
    )
    custom_role_id: int | None = Field(
        None,
        description="使用用户保存的自定义角色ID"
    )
    # 兼容旧版：直接覆盖配置
    override_name: str | None = None
    override_system_prompt: str | None = None
    override_dimensions: list[dict] | None = None


class WorkflowMatchRequest(BaseModel):
    """单个工作流匹配请求"""
    position_id: int
    candidate_ids: list[int] = Field(..., min_length=1, max_length=20)
    role_config: WorkflowRoleConfig | None = None


class WorkflowBatchRequest(BaseModel):
    """批量工作流匹配请求（职位下所有候选人）"""
    position_id: int
    role_config: WorkflowRoleConfig | None = None
    min_score: int = Field(0, ge=0, le=100)


class WorkflowMatchResult(BaseModel):
    candidate_id: int
    candidate_name: str
    score: int
    analysis: str
    dimension_scores: dict[str, int] | None = None
    matched_at: str | None = None
    error: str | None = None


class WorkflowBatchResult(BaseModel):
    position_id: int
    total_count: int
    matched_count: int
    failed_count: int = 0
    failed_reasons: list[str] = Field(default_factory=list)
    avg_score: float
    results: list[WorkflowMatchResult]
    role_name: str


# ==================== 角色列表 API（合并内置+自定义） ====================

@router.get("/roles")
def list_all_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取所有可用角色：内置预设 + 用户自定义
    返回格式中 is_builtin 区分来源
    """
    # 内置预设
    builtin_items = []
    for key, val in BUILTIN_ROLE_PRESETS.items():
        builtin_items.append({
            "id": f"builtin_{key}",
            "role_key": key,
            "name": val["name"],
            "description": val["description"],
            "is_builtin": True,
            "dimensions_count": len(val["eval_dimensions"]),
            "can_edit": False,
            "can_delete": False,
        })

    # 自定义角色
    custom_rows = db.query(WorkflowRoleModel).filter(
        WorkflowRoleModel.user_id == current_user.id,
        WorkflowRoleModel.is_builtin == 0,
    ).order_by(WorkflowRoleModel.sort_order.asc(), WorkflowRoleModel.id.asc()).all()

    custom_items = []
    for row in custom_rows:
        dims = row.eval_dimensions
        custom_items.append({
            "id": row.id,
            "role_key": None,
            "name": row.name,
            "description": row.description or "",
            "is_builtin": False,
            "dimensions_count": len(dims) if dims else 0,
            "can_edit": True,
            "can_delete": True,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        })

    return {
        "builtin_count": len(builtin_items),
        "custom_count": len(custom_items),
        "roles": builtin_items + custom_items,
    }


@router.get("/roles/{role_identifier}")
def get_role_detail(role_identifier: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    获取角色详细配置
    role_identifier 格式:
      - "builtin_recruiter" -> 内置角色
      - "123" (纯数字)     -> 自定义角色ID
    """
    # 判断是内置还是自定义
    if role_identifier.startswith("builtin_"):
        key = role_identifier[len("builtin_"):]
        if key not in BUILTIN_ROLE_PRESETS:
            raise HTTPException(status_code=404, detail=f"内置角色「{key}」不存在")
        preset = BUILTIN_ROLE_PRESETS[key]
        return {
            "id": role_identifier,
            "role_key": key,
            "name": preset["name"],
            "description": preset["description"],
            "is_builtin": True,
            "system_prompt": preset["system_prompt"],
            "eval_dimensions": preset["eval_dimensions"],
            "can_edit": False,
            "can_delete": False,
        }
    # 尝试作为自定义角色ID解析
    try:
        role_id = int(role_identifier)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"角色标识「{role_identifier}」无效")

    role = db.query(WorkflowRoleModel).filter(
        WorkflowRoleModel.id == role_id,
        WorkflowRoleModel.user_id == current_user.id,
    ).first()
    if not role:
        raise HTTPException(status_code=404, detail=f"自定义角色不存在")

    return {
        "id": role.id,
        "role_key": None,
        "name": role.name,
        "description": role.description or "",
        "is_builtin": False,
        "system_prompt": role.system_prompt,
        "eval_dimensions": role.eval_dimensions,
        "can_edit": True,
        "can_delete": True,
        "created_at": role.created_at.isoformat() if role.created_at else None,
        "updated_at": role.updated_at.isoformat() if role.updated_at else None,
    }


# ==================== 自定义角色 CRUD API ====================

@router.post("/roles/custom", status_code=201)
def create_custom_role(
    req: RoleCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新建自定义角色"""
    # 校验维度总分合理性
    dim_list = [d.model_dump() for d in req.eval_dimensions]
    total_max = sum(d.max_score for d in req.eval_dimensions)

    # 计算排序序号（排在最后）
    max_order = db.query(WorkflowRoleModel.sort_order).filter(
        WorkflowRoleModel.user_id == current_user.id,
    ).order_by(WorkflowRoleModel.sort_order.desc()).first()
    next_sort = (max_order[0] if max_order else 0) + 1

    role = WorkflowRoleModel(
        user_id=current_user.id,
        name=req.name,
        description=req.description,
        system_prompt=req.system_prompt,
        eval_dimensions_json=json.dumps(dim_list, ensure_ascii=False),
        is_builtin=0,
        sort_order=next_sort,
    )
    db.add(role)
    db.commit()
    db.refresh(role)

    logger.info(f"用户 {current_user.username} 创建了自定义角色: {req.name} (ID={role.id})")
    return {
        "id": role.id,
        "name": role.name,
        "message": "自定义角色已创建",
        "dimensions_total_max": total_max,
    }


@router.put("/roles/custom/{role_id}")
def update_custom_role(
    role_id: int,
    req: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改自定义角色"""
    role = db.query(WorkflowRoleModel).filter(
        WorkflowRoleModel.id == role_id,
        WorkflowRoleModel.user_id == current_user.id,
        WorkflowRoleModel.is_builtin == 0,
    ).first()
    if not role:
        raise HTTPException(status_code=404, detail="自定义角色不存在或无权操作")

    if req.name is not None:
        role.name = req.name
    if req.description is not None:
        role.description = req.description
    if req.system_prompt is not None:
        role.system_prompt = req.system_prompt
    if req.eval_dimensions is not None:
        role.eval_dimensions_json = json.dumps([d.model_dump() for d in req.eval_dimensions], ensure_ascii=False)

    db.commit()
    db.refresh(role)
    logger.info(f"用户 {current_user.username} 更新了自定义角色 ID={role_id}")
    return {
        "id": role.id,
        "name": role.name,
        "message": "角色已更新",
    }


@router.delete("/roles/custom/{role_id}")
def delete_custom_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除自定义角色"""
    role = db.query(WorkflowRoleModel).filter(
        WorkflowRoleModel.id == role_id,
        WorkflowRoleModel.user_id == current_user.id,
        WorkflowRoleModel.is_builtin == 0,
    ).first()
    if not role:
        raise HTTPException(status_code=404, detail="自定义角色不存在或无权操作")

    deleted_name = role.name
    db.delete(role)
    db.commit()
    logger.info(f"用户 {current_user.username} 删除了自定义角色「{deleted_name}」(ID={role_id})")
    return {"message": f"角色「{deleted_name}」已删除"}


@router.put("/roles/custom/reorder")
def reorder_custom_roles(
    role_ids: list[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """调整自定义角色的排序顺序"""
    if len(role_ids) > 50:
        raise HTTPException(status_code=400, detail="一次最多调整50条记录的顺序")

    for idx, rid in enumerate(role_ids):
        db.query(WorkflowRoleModel).filter(
            WorkflowRoleModel.id == rid,
            WorkflowRoleModel.user_id == current_user.id,
        ).update({"sort_order": idx}, synchronize_session=False)

    db.commit()
    return {"message": "排序已更新"}


# ==================== 核心匹配逻辑 ====================

def _resolve_role_config(
    role_config: WorkflowRoleConfig | None,
    db: Session,
    user_id: int,
) -> dict:
    """
    解析并返回最终的角色配置（合并内置/自定义/覆盖）
    Returns:
        {
            "name": str,
            "system_prompt": str,
            "eval_dimensions": list[dict],
            "source": "builtin"|"custom"|override",
            "role_key_or_id": str|int,
        }
    """
    rc = role_config or WorkflowRoleConfig()

    # 优先级1: 自定义角色ID
    if rc.custom_role_id:
        role = db.query(WorkflowRoleModel).filter(
            WorkflowRoleModel.id == rc.custom_role_id,
            WorkflowRoleModel.user_id == user_id,
        ).first()
        if role:
            return {
                "name": role.name,
                "system_prompt": role.system_prompt,
                "eval_dimensions": role.eval_dimensions,
                "source": "custom",
                "role_key_or_id": role.id,
            }
        # 角色不存在则回退到默认

    # 优先级2: 内置角色类型
    if rc.builtin_role_type and rc.builtin_role_type in BUILTIN_ROLE_PRESETS:
        preset = BUILTIN_ROLE_PRESETS[rc.builtin_role_type]
        result = {
            "name": preset["name"],
            "system_prompt": preset["system_prompt"],
            "eval_dimensions": preset["eval_dimensions"],
            "source": "builtin",
            "role_key_or_id": rc.builtin_role_type,
        }
        # 支持覆盖名称和提示词
        if rc.override_name:
            result["name"] = rc.override_name
        if rc.override_system_prompt:
            result["system_prompt"] = rc.override_system_prompt
        if rc.override_dimensions:
            result["eval_dimensions"] = rc.override_dimensions
        return result

    # 默认：资深招聘专家
    default_preset = BUILTIN_ROLE_PRESETS["recruiter"]
    return {
        "name": default_preset["name"],
        "system_prompt": default_preset["system_prompt"],
        "eval_dimensions": default_preset["eval_dimensions"],
        "source": "builtin",
        "role_key_or_id": "recruiter",
    }


def _build_workflow_match_prompt(
    position: Position,
    candidate_dict: dict,
    educations: list[dict],
    experiences: list[dict],
    skills: list[dict],
    resolved_role: dict,
) -> tuple[str, dict]:
    """根据解析后的角色构建匹配Prompt"""
    dimensions = resolved_role["eval_dimensions"]

    dim_texts = []
    for i, dim in enumerate(dimensions, 1):
        dim_texts.append(f"{i}. **{dim['name']}** (0-{dim['max_score']}分)：{dim['desc']}")

    prompt = f"""{resolved_role['system_prompt']}

请根据以下岗位JD和候选人简历，以「{resolved_role['name']}」的视角评估两者的匹配度。

## 岗位信息
**职位名称**: {position.title}
**部门**: {position.department or '未指定'}
**工作地点**: {position.location or '未限制'}
**薪资范围**: {position.salary_range or '面议'}

**岗位JD**:
{position.job_description or '未填写详细描述'}

**任职要求**:
{position.requirements or '详见职位描述'}

## 候选人信息
**姓名**: {candidate_dict.get('name', '')}
**当前职位**: {candidate_dict.get('current_position', '未知')}
**当前公司**: {candidate_dict.get('current_company', '未知')}
**工作年限**: {candidate_dict.get('work_years', 0) or 0}年
**自我评价**: {candidate_dict.get('self_evaluation', '无') or '无'}

**教育经历**:
{build_educations_text(educations)}

**工作经历**:
{build_experiences_text(experiences)}

**技能标签**:
{build_skills_text(skills)}

## 打分维度（请逐一评估并给出分数）
{chr(10).join(dim_texts)}

## 输出格式
请严格按照以下JSON格式输出：
{{
  "score": 75,
  "has_relevant_experience": true,
  "dimension_scores": {{{_dim_score_example(dimensions)}}},
  "analysis": "## 匹配度分析\\n\\n### 优势\\n1. ...\\n\\n### 不足\\n1. ...\\n\\n### 综合建议\\n..."
}}

## 注意事项
- 总分score必须是0-100之间的整数
- dimension_scores 中每个维度的分数不得超过该维度的满分上限
- analysis 使用Markdown格式，包含详细的匹配分析
- has_relevant_experience: 候选人过往工作/项目经验中是否有与本岗位核心职责直接相关的内容（true/false）"""

    return prompt, {dim["name"]: dim["max_score"] for dim in dimensions}


def _dim_score_example(dimensions: list[dict]) -> str:
    """生成dimension_scores示例值"""
    if not dimensions:
        return '"综合匹配度": 50'
    parts = [f'"{d["name"]}": {d["max_score"] // 2}' for d in dimensions[:3]]
    example = ", ".join(parts)
    return example


# ==================== 匹配执行API ====================

@router.post("/match", response_model=list[WorkflowMatchResult])
def workflow_match(
    req: WorkflowMatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """工作流模式下批量匹配（指定候选人列表）"""
    position = db.query(Position).filter(
        Position.id == req.position_id,
        Position.user_id == current_user.id,
    ).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")

    resolved_role = _resolve_role_config(req.role_config, db, current_user.id)
    results = []
    now_iso = datetime.now().isoformat()

    for cid in req.candidate_ids:
        try:
            candidate = db.query(Candidate).filter(
                Candidate.id == cid, Candidate.user_id == current_user.id,
            ).first()
            if not candidate:
                results.append(WorkflowMatchResult(candidate_id=cid, candidate_name=f"#{cid}(不存在)",
                    score=0, analysis="", error="候选人不存在"))
                continue

            edu_list = _pack_education(db, candidate.id)
            exp_list = _pack_experience(db, candidate.id)
            skill_list = _pack_skill(db, candidate.id)

            result = _execute_workflow_match(
                db=db, position=position, candidate={
                    "name": candidate.name, "current_position": candidate.current_position,
                    "current_company": candidate.current_company, "work_years": candidate.work_years,
                    "self_evaluation": candidate.self_evaluation,
                }, educations=edu_list, experiences=exp_list, skills=skill_list,
                resolved_role=resolved_role, candidate_obj=candidate, user_id=current_user.id,
            )
            results.append(WorkflowMatchResult(candidate_id=candidate.id, candidate_name=candidate.name,
                score=result["score"], analysis=result["analysis"], dimension_scores=result.get("dimension_scores"),
                matched_at=now_iso))
        except Exception as e:
            logger.error(f"工作流匹配失败 cid={cid}: {e}")
            results.append(WorkflowMatchResult(candidate_id=cid, candidate_name=f"#{cid}",
                score=0, analysis="", error=str(e)))
    return results


@router.post("/match/all", response_model=WorkflowBatchResult)
def workflow_match_all(
    req: WorkflowBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """工作流模式下全量匹配某职位的所有候选人"""
    position = db.query(Position).filter(
        Position.id == req.position_id, Position.user_id == current_user.id,
    ).first()
    if not position:
        raise HTTPException(status_code=404, detail="职位不存在")

    candidates = db.query(Candidate).filter(
        Candidate.user_id == current_user.id, Candidate.position_id == req.position_id,
    ).all()
    if not candidates:
        return WorkflowBatchResult(position_id=req.position_id, total_count=0, matched_count=0,
            failed_count=0, failed_reasons=[],
            avg_score=0.0, results=[], role_name="—")

    resolved_role = _resolve_role_config(req.role_config, db, current_user.id)
    results, matched_count, total_score = [], 0, 0
    failed_count = 0
    failed_reasons = []
    now_iso = datetime.now().isoformat()

    for candidate in candidates:
        # 跳过已成功匹配的，避免重复消耗 token（但如果失败过可以重试，所以只跳过有 score 的）
        existing = db.query(MatchResult).filter(
            MatchResult.candidate_id == candidate.id,
            MatchResult.position_id == position.id,
        ).first()
        if existing and existing.score is not None and existing.score > 0:
            # 已匹配成功，直接复用
            matched_count += 1
            total_score += existing.score
            # 复用历史 dimension_scores（从 analysis 文本里解出）
            dim_reuse = None
            if existing.analysis:
                import re as _re
                m = _re.search(r"\[DIM_SCORES\](.*?)\[/DIM_SCORES\]", existing.analysis, _re.DOTALL)
                if m:
                    try:
                        dim_reuse = json.loads(m.group(1))
                    except Exception:
                        dim_reuse = None
            results.append(WorkflowMatchResult(
                candidate_id=candidate.id, candidate_name=candidate.name,
                score=existing.score, analysis=existing.analysis or "",
                dimension_scores=dim_reuse, matched_at=now_iso
            ))
            continue

        try:
            edu_list = _pack_education(db, candidate.id)
            exp_list = _pack_experience(db, candidate.id)
            skill_list = _pack_skill(db, candidate.id)

            # 提前检查：简历文本为空 / 无姓名 / 无 position_id 时直接标记失败，不浪费 token
            if not candidate.resume_raw_text or not candidate.resume_raw_text.strip():
                raise ValueError("简历文本为空（未成功解析）")
            if not candidate.name or candidate.name.startswith("未命名") or candidate.name.endswith(".pdf") or candidate.name.endswith(".doc") or candidate.name.endswith(".docx"):
                raise ValueError(f"候选人姓名异常（{candidate.name}），请先完成简历解析")

            result = _execute_workflow_match(db=db, position=position, candidate={
                "name": candidate.name, "current_position": candidate.current_position,
                "current_company": candidate.current_company, "work_years": candidate.work_years,
                "self_evaluation": candidate.self_evaluation,
            }, educations=edu_list, experiences=exp_list, skills=skill_list,
            resolved_role=resolved_role, candidate_obj=candidate, user_id=current_user.id)
            if result["score"] < req.min_score:
                # 低于阈值也写入结果（用 0 分占位），避免重试
                dim_marker = f"[DIM_SCORES]{json.dumps(result.get('dimension_scores') or {}, ensure_ascii=False)}[/DIM_SCORES]\n\n"
                if existing:
                    existing.score = result["score"]
                    existing.analysis = dim_marker + (result.get("analysis") or "")
                else:
                    db.add(MatchResult(
                        candidate_id=candidate.id, position_id=position.id,
                        score=result["score"],
                        analysis=dim_marker + (result.get("analysis") or "")
                    ))
                db.commit()
                continue
            matched_count += 1
            total_score += result["score"]
            results.append(WorkflowMatchResult(
                candidate_id=candidate.id, candidate_name=candidate.name,
                score=result["score"], analysis=result["analysis"],
                dimension_scores=result.get("dimension_scores"),
                matched_at=now_iso
            ))
        except Exception as e:
            failed_count += 1
            err_msg = str(e)
            logger.error(f"批量匹配失败 cid={candidate.id}: {err_msg}")
            failed_reasons.append(f"{candidate.name or '#'+str(candidate.id)}: {err_msg[:80]}")
            try:
                db.rollback()
            except Exception:
                pass
            # 写入一条"匹配失败"的占位记录（score=-1），下次可以重试
            fail_marker = f"[DIM_SCORES]{json.dumps({}, ensure_ascii=False)}[/DIM_SCORES]\n\n" \
                          f"⚠️ 本次匹配失败：{err_msg[:200]}\n\n请检查候选人简历是否已成功解析，或重新点击「一键打分」。"
            if existing:
                existing.score = 0
                existing.analysis = fail_marker
            else:
                db.add(MatchResult(
                    candidate_id=candidate.id, position_id=position.id,
                    score=0, analysis=fail_marker
                ))
            try:
                db.commit()
            except Exception:
                db.rollback()

    results.sort(key=lambda x: -x.score)
    return WorkflowBatchResult(
        position_id=req.position_id, total_count=len(candidates),
        matched_count=matched_count, failed_count=failed_count,
        failed_reasons=failed_reasons[:20],
        avg_score=round(total_score/matched_count, 1) if matched_count else 0.0,
        results=results[:50], role_name=resolved_role["name"]
    )


def _execute_workflow_match(db, position, candidate, educations, experiences, skills, resolved_role, candidate_obj, user_id: int) -> dict:
    from app.services.ai_client import get_user_ai_client

    client = get_user_ai_client(db, user_id)
    prompt, dim_max_scores = _build_workflow_match_prompt(
        position=position, candidate_dict=candidate, educations=educations,
        experiences=experiences, skills=skills, resolved_role=resolved_role,
    )
    if len(prompt) > 15000: prompt = prompt[:15000]

    messages = [
        {"role": "system", "content": "你是专业的招聘评估专家。输出必须为合法JSON格式。"},
        {"role": "user", "content": prompt},
    ]
    try:
        raw_result = client.chat_json(messages, temperature=0.3)
        score = max(0, min(100, int(raw_result.get("score", 0))))
        analysis = raw_result.get("analysis", "")
        dim_scores = raw_result.get("dimension_scores", {})
        has_relevant_exp = bool(raw_result.get("has_relevant_experience", False))

        # 兜底：若AI未返回分析文本，构造一个基于维度分数的简要分析
        if not analysis or not analysis.strip():
            analysis_lines = [f"## 匹配评估报告 (角色:{resolved_role['name']})", "", f"**综合得分: {score}**", "", "### 各维度得分"]
            for dim_name, dim_score in (dim_scores.items() if isinstance(dim_scores, dict) else []):
                max_val = dim_max_scores.get(dim_name, "?")
                analysis_lines.append(f"- {dim_name}：{dim_score} / {max_val}")
            analysis_lines.extend([
                "",
                "### 综合评价",
                f"基于「{resolved_role['name']}」评估视角，候选人综合得分为 {score} 分。"
                + ("建议进入下一轮面试环节。" if score >= 60 else "匹配度偏低，建议谨慎评估。"),
            ])
            analysis = "\n".join(analysis_lines)
        for dn, mv in dim_max_scores.items():
            if dn in dim_scores: dim_scores[dn] = min(int(dim_scores[dn]), mv)

        existing = db.query(MatchResult).filter(
            MatchResult.candidate_id == candidate_obj.id, MatchResult.position_id == position.id,
        ).first()
        # 在 analysis 开头插入维度分数和"相关经验"标记，方便前端读出
        dim_marker = f"[DIM_SCORES]{json.dumps(dim_scores, ensure_ascii=False)}[/DIM_SCORES]\n"
        exp_marker = f"[HAS_RELEVANT_EXP]{'true' if has_relevant_exp else 'false'}[/HAS_RELEVANT_EXP]\n"
        full_analysis = dim_marker + exp_marker + analysis
        if existing: existing.score = score; existing.analysis = full_analysis
        else: db.add(MatchResult(candidate_id=candidate_obj.id, position_id=position.id, score=score, analysis=full_analysis))
        db.commit()
        return {"score": score, "analysis": analysis, "dimension_scores": dim_scores, "has_relevant_experience": has_relevant_exp}
    except Exception as e:
        logger.error(f"工作流AI匹配失败: {e}")
        fallback = match_candidate_to_position(
            position={"title": position.title, "department": position.department, "location": position.location,
                      "salary_range": position.salary_range, "job_description": position.job_description,
                      "requirements": position.requirements},
            candidate=candidate, educations=educations, experiences=experiences, skills=skills,
            db=db,
            user_id=user_id,
        )
        fallback["analysis"] += "\n\n> 工作流AI接口异常，已降级使用基础匹配算法。"
        return fallback


# ==================== 数据打包辅助函数 ====================

def _pack_education(db, candidate_id):
    rows = db.query(CandidateEducation).filter(CandidateEducation.candidate_id == candidate_id).all()
    return [{"school": e.school, "degree": e.degree, "major": e.major, "start_date": e.start_date, "end_date": e.end_date} for e in rows]


def _pack_experience(db, candidate_id):
    rows = db.query(CandidateExperience).filter(CandidateExperience.candidate_id == candidate_id).all()
    return [{"company": e.company, "position": e.position, "start_date": e.start_date, "end_date": e.end_date, "description": e.description} for e in rows]


def _pack_skill(db, candidate_id):
    rows = db.query(CandidateSkill).filter(CandidateSkill.candidate_id == candidate_id).all()
    return [{"skill_name": s.skill_name, "proficiency": s.proficiency} for s in rows]
