"""Per-task deterministic request and output-token reservation limits."""
from contextvars import ContextVar
from dataclasses import dataclass, field
from app.runtime.model_usage import BudgetExceeded, ModelUsageBudget


@dataclass
class TaskBudget:
    max_tools: int = 100
    max_models: int = 10
    max_output_tokens: int = 8000
    tools: int = 0
    models: int = 0
    output_tokens: int = 0
    exhausted: bool = False
    usage: ModelUsageBudget = field(default_factory=ModelUsageBudget)

    def check(self):
        if self.exhausted or self.usage.exhausted:
            raise BudgetExceeded("task budget exhausted")

    def reserve(self, *, model=False, output_tokens=0):
        self.check()
        if (self.tools + 1 > self.max_tools
                or self.models + int(model) > self.max_models
                or self.output_tokens + output_tokens > self.max_output_tokens):
            self.exhausted = True
            self.check()
        self.tools += 1
        self.models += int(model)
        self.output_tokens += output_tokens


active_budget: ContextVar[TaskBudget | None] = ContextVar("agent_budget", default=None)


def reserve(*, model=False, output_tokens=0):
    budget = active_budget.get()
    if budget is not None:
        budget.reserve(model=model, output_tokens=output_tokens)


def reserve_model(model: str, text: str, pictures: int = 0, output_tokens: int = 0):
    budget = active_budget.get()
    if budget is not None:
        budget.usage.reserve(model, text, pictures, output_tokens)
        budget.reserve(model=True, output_tokens=output_tokens)


def record_usage(model: str, body: dict):
    budget = active_budget.get()
    if budget is not None:
        budget.usage.record(model, body)
        if budget.usage.reported_output > budget.max_output_tokens:
            budget.exhausted = True
            raise BudgetExceeded("reported output tokens exceeded budget")
