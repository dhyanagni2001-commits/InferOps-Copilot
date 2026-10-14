"""Validated API and workflow data models."""

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


class Workload(BaseModel):
    kind: Literal["Deployment", "StatefulSet", "DaemonSet", "Pod", "Service"]
    name: str = Field(min_length=1, max_length=253, pattern=r"^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$")


class DiagnoseRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    namespace: str = Field(min_length=1, max_length=63)
    workload: Workload

    @field_validator("namespace")
    @classmethod
    def valid_namespace(cls, value: str) -> str:
        if not value.replace("-", "").isalnum() or value.lower() != value:
            raise ValueError("namespace must be a lowercase Kubernetes name")
        return value


class Evidence(BaseModel):
    id: str
    source: str
    title: str
    detail: str
    data: dict[str, Any] = Field(default_factory=dict)


class Diagnosis(BaseModel):
    summary: str
    evidence_ids: list[str]
    suggested_actions: list[str]
    limitations: list[str] = Field(default_factory=list)


class DiagnosticResult(BaseModel):
    request_id: str
    status: Literal["completed"] = "completed"
    diagnosis: Diagnosis
    evidence: list[Evidence]
