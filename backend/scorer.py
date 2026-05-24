"""C-SSRS 评分引擎 — 5层评分逻辑"""
from dataclasses import dataclass, field, asdict
from datetime import date
from enum import Enum
from typing import Optional


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── 输入数据结构 ──

@dataclass
class IdeationAnswers:
    i1_wish_dead: bool = False
    i1_onset: Optional[str] = None
    i1_duration: Optional[str] = None
    i1_frequency: Optional[int] = None

    i2_non_specific: bool = False
    i2_nature: Optional[str] = None
    i2_frequency: Optional[int] = None
    i2_duration: Optional[int] = None

    i3_with_method: bool = False
    i3_method: Optional[str] = None
    i3_location: Optional[str] = None
    i3_timing: Optional[str] = None

    i4_with_intent: bool = False
    i4_intent_strength: Optional[int] = None

    i5_with_plan_and_intent: bool = False


@dataclass
class IntensityAnswers:
    frequency: int = 0
    duration: int = 0
    controllability: int = 0
    deterrents: int = 0
    reason: int = 0


@dataclass
class BehaviorAnswers:
    b1_actual_attempt: bool = False
    b1_date: Optional[str] = None
    b1_method: Optional[str] = None
    b1_medical_damage: bool = False
    b1_lethal_intent: bool = False
    b1_medical_intervention: bool = False

    b2_interrupted: bool = False
    b2_date: Optional[str] = None
    b2_method: Optional[str] = None
    b2_interrupted_by: Optional[str] = None

    b3_aborted: bool = False
    b3_date: Optional[str] = None
    b3_method: Optional[str] = None
    b3_stopped_by: Optional[str] = None

    b4_preparatory: bool = False
    b4_behavior: Optional[str] = None
    b4_date: Optional[str] = None
    b4_has_plan: bool = False

    b5_nssi: bool = False
    b5_behavior_type: Optional[str] = None
    b5_frequency: Optional[str] = None
    b5_motivation: Optional[str] = None


# ── 输出结果 ──

@dataclass
class AssessmentResult:
    session_id: str
    patient_id: str
    assessment_date: str
    screener_result: str
    ideation_severity_score: int
    ideation_severity_name: str
    intensity_total: int
    intensity_level: str
    behavior_types_positive: list[str] = field(default_factory=list)
    lethality_level: int = 0
    risk_level: str = ""
    risk_label_zh: str = ""
    immediate_actions: list[str] = field(default_factory=list)
    follow_up_plan: str = ""
    documentation_required: str = ""
    warning_signals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "patient_id": self.patient_id,
            "assessment_date": self.assessment_date,
            "screener_result": self.screener_result,
            "ideation_severity": {"score": self.ideation_severity_score, "name": self.ideation_severity_name},
            "intensity": {"total": self.intensity_total, "level": self.intensity_level},
            "behavior_positive": self.behavior_types_positive,
            "lethality_level": self.lethality_level,
            "risk_level": self.risk_level,
            "risk_label": self.risk_label_zh,
            "immediate_actions": self.immediate_actions,
            "follow_up": self.follow_up_plan,
            "documentation": self.documentation_required,
            "warning_signals": self.warning_signals,
        }


# ── 评分函数 ──

_SEVERITY_LEVELS = [
    (5, "有计划有意图的主动自杀意念", "重度", "high"),
    (4, "有意图但无计划的主动自杀意念", "中重度", "high"),
    (3, "有方法的主动自杀意念", "中度", "medium"),
    (2, "非特定的主动自杀意念", "轻中度", "low"),
    (1, "渴望死亡", "轻度", "low"),
    (0, "无自杀意念", "无", "none"),
]


def calculate_severity(ideation: IdeationAnswers) -> tuple[int, str]:
    """从I5向下检查，第一个"是"即为严重度等级"""
    if ideation.i5_with_plan_and_intent:
        return 5, "有计划有意图的主动自杀意念"
    if ideation.i4_with_intent:
        return 4, "有意图但无计划的主动自杀意念"
    if ideation.i3_with_method:
        return 3, "有方法的主动自杀意念"
    if ideation.i2_non_specific:
        return 2, "非特定的主动自杀意念"
    if ideation.i1_wish_dead:
        return 1, "渴望死亡"
    return 0, "无自杀意念"


def calculate_intensity(intensity: IntensityAnswers) -> tuple[int, str]:
    total = (intensity.frequency + intensity.duration +
             intensity.controllability + intensity.deterrents +
             intensity.reason)
    if total <= 9:
        return total, "低强度"
    elif total <= 14:
        return total, "中等强度"
    else:
        return total, "高强度"


def get_intensity_red_flags(intensity: IntensityAnswers) -> list[str]:
    flags = []
    if intensity.controllability == 5:
        flags.append("完全无法控制自杀意念")
    if intensity.reason >= 4:
        flags.append("有准备或即将行动的倾向")
    if intensity.deterrents == 5:
        flags.append("完全没有任何阻遏因素")
    return flags


def get_behavior_positive(behavior: BehaviorAnswers) -> list[str]:
    result = []
    if behavior.b1_actual_attempt:
        result.append("B1-实际尝试")
    if behavior.b2_interrupted:
        result.append("B2-中断尝试")
    if behavior.b3_aborted:
        result.append("B3-中止尝试")
    if behavior.b4_preparatory:
        result.append("B4-准备行为")
    if behavior.b5_nssi:
        result.append("B5-非自杀性自伤")
    return result


_ACTIONS = {
    RiskLevel.CRITICAL: ["立即住院治疗", "24小时看护", "通知家属/监护人", "移除所有危险物品", "制定住院安全计划"],
    RiskLevel.HIGH: ["立即精神科紧急评估（2-24小时内）", "通知家属/监护人", "制定安全计划", "考虑住院"],
    RiskLevel.MEDIUM: ["精神科评估（24-72小时内）", "制定安全计划", "增加随访频率", "评估是否需要住院"],
    RiskLevel.LOW: ["加强监测", "制定安全计划（1周内）", "根据患者意愿决定是否通知家属"],
    RiskLevel.NONE: ["常规随访"],
}

_FOLLOW_UP = {
    RiskLevel.CRITICAL: "出院后24-48小时内随访",
    RiskLevel.HIGH: "每周随访",
    RiskLevel.MEDIUM: "每2周随访",
    RiskLevel.LOW: "每月随访",
    RiskLevel.NONE: "按常规计划",
}

_DOCS = {
    RiskLevel.CRITICAL: "完整风险评估报告",
    RiskLevel.HIGH: "风险评估报告 + 安全计划",
    RiskLevel.MEDIUM: "安全计划 + 随访记录",
    RiskLevel.LOW: "随访记录",
    RiskLevel.NONE: "筛查记录归档",
}

_RISK_LABELS = {
    RiskLevel.CRITICAL: "极高风险",
    RiskLevel.HIGH: "高风险",
    RiskLevel.MEDIUM: "中等风险",
    RiskLevel.LOW: "低风险",
    RiskLevel.NONE: "无风险",
}


def determine_risk(
    severity: int,
    intensity_total: int,
    behavior: BehaviorAnswers,
    lethality: int = 0,
    red_flags: list[str] | None = None,
) -> RiskLevel:
    """综合风险判定引擎"""
    red_flags = red_flags or []

    if behavior.b1_actual_attempt:
        return RiskLevel.CRITICAL
    if severity == 5 and behavior.b4_preparatory:
        return RiskLevel.CRITICAL
    if lethality >= 4:
        return RiskLevel.CRITICAL

    if severity >= 4:
        return RiskLevel.HIGH
    if behavior.b2_interrupted or behavior.b3_aborted:
        return RiskLevel.HIGH
    if intensity_total >= 20:
        return RiskLevel.HIGH
    if 2 <= lethality <= 3:
        return RiskLevel.HIGH

    if severity == 3:
        return RiskLevel.MEDIUM
    if behavior.b4_preparatory:
        return RiskLevel.MEDIUM
    if behavior.b5_nssi:
        return RiskLevel.MEDIUM
    if intensity_total >= 15:
        return RiskLevel.MEDIUM

    if severity in (1, 2):
        return RiskLevel.LOW
    if intensity_total >= 10:
        return RiskLevel.LOW

    return RiskLevel.NONE


def score_assessment(
    session_id: str,
    patient_id: str,
    ideation: IdeationAnswers,
    intensity: IntensityAnswers,
    behavior: BehaviorAnswers,
    lethality: int = 0,
) -> AssessmentResult:
    """完整评分流程"""
    screener = "positive" if ideation.i1_wish_dead else "negative"
    severity_score, severity_name = calculate_severity(ideation)
    has_ideation = ideation.i1_wish_dead

    if has_ideation:
        intensity_total, intensity_level = calculate_intensity(intensity)
        red_flags = get_intensity_red_flags(intensity)
    else:
        intensity_total, intensity_level = 0, "不适用"
        red_flags = []

    behavior_positive = get_behavior_positive(behavior)

    risk_level = determine_risk(
        severity=severity_score,
        intensity_total=intensity_total,
        behavior=behavior,
        lethality=lethality,
        red_flags=red_flags,
    )

    return AssessmentResult(
        session_id=session_id,
        patient_id=patient_id,
        assessment_date=str(date.today()),
        screener_result=screener,
        ideation_severity_score=severity_score,
        ideation_severity_name=severity_name,
        intensity_total=intensity_total,
        intensity_level=intensity_level,
        behavior_types_positive=behavior_positive,
        lethality_level=lethality,
        risk_level=risk_level.value,
        risk_label_zh=_RISK_LABELS[risk_level],
        immediate_actions=_ACTIONS[risk_level],
        follow_up_plan=_FOLLOW_UP[risk_level],
        documentation_required=_DOCS[risk_level],
        warning_signals=red_flags,
    )
