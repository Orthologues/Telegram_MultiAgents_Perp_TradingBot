"""Canonical owner-selected QWEN and shared Ministral Crew composition."""

from __future__ import annotations

import os

from crewai import LLM, Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, field_validator

from crewai_app.domain.contracts.schemas import (
    ACCEPTABLE_ALTERNATIVE_OWNER_MODEL_IDS,
    BedrockModelId,
    OwnerId,
    QwenStrategyCandidateSet,
)
from crewai_app.flows.states import MinistralStrategyReviewSet

_OWNER_AGENT_CONFIG = {
    OwnerId.OWNER_A_SHU_QIN: "owner_a_qwen",
    OwnerId.OWNER_B_LAO_TU: "owner_b_qwen",
    OwnerId.OWNER_C_BI_JIA_SUO: "owner_c_qwen",
    OwnerId.OWNER_D_A_ZHU: "owner_d_qwen",
}

_OWNER_MODEL_ENV = {
    OwnerId.OWNER_A_SHU_QIN: "CREWAI_QWEN_OWNER_A_MODEL_ID",
    OwnerId.OWNER_B_LAO_TU: "CREWAI_QWEN_OWNER_B_MODEL_ID",
    OwnerId.OWNER_C_BI_JIA_SUO: "CREWAI_QWEN_OWNER_C_MODEL_ID",
    OwnerId.OWNER_D_A_ZHU: "CREWAI_QWEN_OWNER_D_MODEL_ID",
}


class CrewModelSettings(BaseModel):
    """IAM-authenticated Bedrock configuration without static credentials."""

    aws_region_name: str = Field(min_length=1)
    owner_qwen_model_ids: dict[OwnerId, str] = Field(
        default_factory=lambda: {
            owner_id: BedrockModelId.QWEN3_VL_235B_A22B for owner_id in OwnerId
        }
    )
    ministral_model_id: str = Field(
        default=BedrockModelId.MINISTRAL_3_8B_INSTRUCT,
        min_length=1,
    )
    timeout_seconds: int = Field(default=60, ge=1, le=300)
    structured_output_retries: int = Field(default=1, ge=0, le=3)

    @field_validator("owner_qwen_model_ids")
    @classmethod
    def validate_owner_models(
        cls,
        model_ids: dict[OwnerId, str],
    ) -> dict[OwnerId, str]:
        if set(model_ids) != set(OwnerId):
            raise ValueError("one Bedrock QWEN model ID is required for each owner")
        if any(not model_id.strip() for model_id in model_ids.values()):
            raise ValueError("Bedrock QWEN model IDs must not be blank")
        allowed_model_ids = {
            BedrockModelId.QWEN3_VL_235B_A22B.value,
        } | {model_id.value for model_id in ACCEPTABLE_ALTERNATIVE_OWNER_MODEL_IDS}
        invalid_model_ids = sorted(
            {model_id for model_id in model_ids.values() if model_id not in allowed_model_ids}
        )
        if invalid_model_ids:
            raise ValueError(
                "owner model IDs must be the Qwen default or an approved multimodal "
                f"alternative: {', '.join(invalid_model_ids)}"
            )
        return model_ids

    @classmethod
    def from_environment(cls) -> CrewModelSettings:
        if os.getenv("CREWAI_BEDROCK_ENABLED", "false").lower() != "true":
            raise RuntimeError("CrewAI Bedrock execution is disabled")
        return cls(
            aws_region_name=_required_environment("AWS_REGION_NAME"),
            owner_qwen_model_ids={
                owner_id: _required_environment(environment_name)
                for owner_id, environment_name in _OWNER_MODEL_ENV.items()
            },
            ministral_model_id=_required_environment("CREWAI_MINISTRAL_MODEL_ID"),
            timeout_seconds=int(
                os.getenv("CREWAI_MODEL_TIMEOUT_SECONDS", "60")
            ),
            structured_output_retries=int(
                os.getenv("CREWAI_STRUCTURED_OUTPUT_RETRIES", "1")
            ),
        )


def build_bedrock_llm(model_id: str, settings: CrewModelSettings) -> LLM:
    """Create a CrewAI LLM that relies on the AWS IAM credential chain."""
    normalized_model_id = (
        model_id if model_id.startswith("bedrock/") else f"bedrock/{model_id}"
    )
    return LLM(
        model=normalized_model_id,
        temperature=0.0,
        timeout=settings.timeout_seconds,
        region_name=settings.aws_region_name,
    )


@CrewBase
class TradingSignalCrew:
    """Sequential Crew containing one selected QWEN and shared Ministral."""

    agents: list[BaseAgent]
    tasks: list[Task]
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(
        self,
        owner_id: OwnerId,
        settings: CrewModelSettings,
        *,
        qwen_tools: list[BaseTool] | None = None,
        ministral_tools: list[BaseTool] | None = None,
    ) -> None:
        self.owner_id = owner_id
        self.settings = settings
        self.qwen_tools = _validate_agent_tools(qwen_tools or [])
        self.ministral_tools = _validate_agent_tools(ministral_tools or [])

    @agent
    def owner_qwen(self) -> Agent:
        return Agent(
            config=self.agents_config[_OWNER_AGENT_CONFIG[self.owner_id]],
            llm=build_bedrock_llm(
                self.settings.owner_qwen_model_ids[self.owner_id],
                self.settings,
            ),
            tools=self.qwen_tools,
            allow_delegation=False,
            max_retry_limit=self.settings.structured_output_retries,
        )

    @agent
    def shared_ministral(self) -> Agent:
        return Agent(
            config=self.agents_config["shared_ministral"],
            llm=build_bedrock_llm(self.settings.ministral_model_id, self.settings),
            tools=self.ministral_tools,
            allow_delegation=False,
            max_retry_limit=self.settings.structured_output_retries,
        )

    @task
    def qwen_strategy_task(self) -> Task:
        return Task(
            config=self.tasks_config["qwen_strategy_task"],
            agent=self.owner_qwen(),
            output_pydantic=QwenStrategyCandidateSet,
        )

    @task
    def ministral_review_task(self) -> Task:
        return Task(
            config=self.tasks_config["ministral_review_task"],
            agent=self.shared_ministral(),
            context=[self.qwen_strategy_task()],
            output_pydantic=MinistralStrategyReviewSet,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.owner_qwen(), self.shared_ministral()],
            tasks=[self.qwen_strategy_task(), self.ministral_review_task()],
            process=Process.sequential,
            memory=False,
            cache=False,
            verbose=False,
            tracing=os.getenv("CREWAI_TRACING_ENABLED", "false").lower() == "true",
        )


def _validate_agent_tools(tools: list[BaseTool]) -> list[BaseTool]:
    forbidden = [tool.name for tool in tools if not getattr(tool, "agent_accessible", False)]
    if forbidden:
        raise ValueError(
            "Flow-only tools cannot be attached to agents: " + ", ".join(forbidden)
        )
    return list(tools)


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise RuntimeError(f"required environment variable is not configured: {name}")
    return value
