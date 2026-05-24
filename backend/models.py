"""Pydantic request/response schemas for the C-SSRS API"""
from pydantic import BaseModel, Field
from typing import Optional


class SessionCreate(BaseModel):
    patient_id: str
    version: str = "baseline"
    session_id: Optional[str] = None  # If provided, use it (for cloud-initiated sessions)


class IdeationInput(BaseModel):
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


class IntensityInput(BaseModel):
    frequency: int = 0
    duration: int = 0
    controllability: int = 0
    deterrents: int = 0
    reason: int = 0


class BehaviorInput(BaseModel):
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


class AssessRequest(BaseModel):
    ideation: IdeationInput
    intensity: IntensityInput
    behavior: BehaviorInput
    lethality: int = 0


class IdeationSeverityResponse(BaseModel):
    score: int
    name: str


class IntensityResponse(BaseModel):
    total: int
    level: str


class AssessmentResponse(BaseModel):
    session_id: str
    patient_id: str
    assessment_date: str
    screener_result: str
    ideation_severity: IdeationSeverityResponse
    intensity: IntensityResponse
    behavior_positive: list[str] = Field(default_factory=list)
    lethality_level: int = 0
    risk_level: str
    risk_label: str
    immediate_actions: list[str] = Field(default_factory=list)
    follow_up: str = ""
    documentation: str = ""
    warning_signals: list[str] = Field(default_factory=list)
