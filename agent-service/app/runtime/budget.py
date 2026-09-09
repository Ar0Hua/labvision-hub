"""Per-task deterministic request and output-token reservation limits."""
from contextvars import ContextVar
from dataclasses import dataclass


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class TaskBudget:
    max_tools: int = 100
    max_models: int = 10
    max_output_tokens: int = 8000
    tools: int = 0
    models: int = 0
    output_tokens: int = 0
    exhausted: bool = False

    def check(self):
        if self.exhausted:
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
