"""Validated API and workflow data models."""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

DNS_LABEL = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
WorkloadKind = Literal["Deployment", "StatefulSet", "DaemonSet", "Pod", "Service"]


class Workload(BaseModel):
    kind: WorkloadKind
    name: str = Field(min_length=1, max_length=253, pattern=r"^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$")


class DiagnoseRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    namespace: str = Field(min_length=1, max_length=63)
    workload: Workload

    @field_validator("namespace")
    @classmethod
    def valid_namespace(cls, value: str) -> str:
        if not DNS_LABEL.match(value):
            raise ValueError("namespace must be a lowercase Kubernetes name")
        return value


class Evidence(BaseModel):
    """One bounded, normalized observation that a diagnosis may cite."""

    id: str
    source: str
    title: str
    detail: str
    data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class Alternative(BaseModel):
    cause: str
    summary: str
    evidence_ids: list[str]


class Diagnosis(BaseModel):
    cause: str
    summary: str
    confidence: Literal["high", "medium", "low"]
    evidence_ids: list[str]
    suggested_actions: list[str]
    commands: list[str] = Field(default_factory=list)
    alternatives: list[Alternative] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    generated_by: Literal["rules", "llm"] = "rules"


class DiagnosticResult(BaseModel):
    request_id: str
    status: Literal["completed"] = "completed"
    mode: Literal["demo", "cluster"]
    duration_ms: float
    diagnosis: Diagnosis
    evidence: list[Evidence]
