"""Conservative preflight reservations and separately reported provider usage."""
from dataclasses import dataclass, field
from decimal import Decimal
import json


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class ModelUsageBudget:
    max_input_tokens: int = 262144
    max_cost: Decimal = Decimal("0")
    image_reservation: int = 8192
    prices: dict = field(default_factory=dict)
    reserved_input: int = 0
    reserved_cost: Decimal = Decimal("0")
    reported_input: int = 0
    reported_output: int = 0
    reported_visual: int = 0
    actual_cost: Decimal = Decimal("0")
    missing_usage: int = 0
    missing_price: bool = False
    reserved_calls: int = 0
    reported_calls: int = 0
    visual_usage_reports: int = 0
    exhausted: bool = False

    @classmethod
    def configured(cls, max_input: int, max_cost: str, prices_json: str, image_tokens: int):
        cost = Decimal(max_cost)
        if not cost.is_finite() or cost < 0 or max_input < 1 or image_tokens < 1:
            raise ValueError("invalid usage budget")
        raw = json.loads(prices_json)
        if not isinstance(raw, dict):
            raise ValueError("model prices must be an object")
        prices = {}
        for model, value in raw.items():
            pair = (Decimal(str(value["inputPerMillion"])), Decimal(str(value["outputPerMillion"])))
            if any(not price.is_finite() or price < 0 for price in pair):
                raise ValueError("invalid model price")
            prices[model] = pair
        return cls(max_input, cost, image_tokens, prices)

    def fail(self, reason):
        self.exhausted = True
        raise BudgetExceeded(reason)

    def reserve(self, model: str, text: str, pictures: int, output: int):
        if self.exhausted:
            self.fail("model budget exhausted")
        # UTF-8 bytes + protocol allowance; visual tokens are configurable reservations,
        # not a claim about actual provider tokenization.
        estimated = len(text.encode("utf-8")) + 512 + pictures * self.image_reservation
        pair = self.prices.get(model)
        if pair is None:
            self.missing_price = True
            if self.max_cost > 0:
                self.fail("cost cap requires configured prices for every model")
        cost = (estimated * pair[0] + output * pair[1]) / Decimal(1000000) if pair else Decimal(0)
        if self.reserved_input + estimated > self.max_input_tokens:
            self.fail("input/visual token reservation exhausted")
        if self.max_cost > 0 and self.reserved_cost + cost > self.max_cost:
            self.fail("cost reservation exhausted")
        self.reserved_input += estimated
        self.reserved_cost += cost
        self.reserved_calls += 1

    def record(self, model: str, body: dict):
        usage = body.get("usage")
        if not isinstance(usage, dict):
            self.missing_usage += 1
            return
        input_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
        output_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
        if (type(input_tokens) is not int or input_tokens < 0
                or type(output_tokens) is not int or output_tokens < 0):
            self.missing_usage += 1
            return
        self.reported_input += input_tokens
        self.reported_output += output_tokens
        self.reported_calls += 1
        details = usage.get("prompt_tokens_details") or {}
        visual = details.get("image_tokens") if isinstance(details, dict) else None
        if type(visual) is int and 0 <= visual <= input_tokens:
            self.reported_visual += visual
            self.visual_usage_reports += 1
        pair = self.prices.get(model)
        if pair:
            self.actual_cost += (input_tokens * pair[0] + output_tokens * pair[1]) / Decimal(1000000)
        else:
            self.missing_price = True
        if self.reported_input > self.max_input_tokens or (self.max_cost > 0 and self.actual_cost > self.max_cost):
            self.fail("reported model usage exceeded budget; further calls stopped")

    def snapshot(self):
        return {"reservedInputTokens": self.reserved_input,
                "reportedInputTokens": self.reported_input, "reportedOutputTokens": self.reported_output,
                "reportedVisualTokens": self.reported_visual if self.visual_usage_reports else None,
                "responsesMissingUsage": self.missing_usage,
                "unreportedOrFailedCalls": max(0,self.reserved_calls-self.reported_calls),
                "reservedCost": None if self.missing_price else str(self.reserved_cost),
                "reportedCost": None if self.missing_price or self.missing_usage or self.reserved_calls!=self.reported_calls else str(self.actual_cost),
                "costCapEnabled": self.max_cost > 0,
                "basis": "configured prices; incomplete provider usage is not zero billing"}
