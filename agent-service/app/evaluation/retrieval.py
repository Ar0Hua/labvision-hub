import argparse
import json
import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GoldenCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    queryId: str = Field(min_length=1, max_length=100)
    relevantPictureIds: list[str] = Field(min_length=1)
    forbiddenPictureIds: list[str] = Field(default_factory=list)

    @field_validator("relevantPictureIds", "forbiddenPictureIds")
    @classmethod
    def valid_ids(cls, values: list[str]) -> list[str]:
        if any(not value.isdigit() or int(value) < 1 for value in values) or len(values) != len(set(values)):
            raise ValueError("picture IDs must be unique positive integer strings")
        return values


class Prediction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    queryId: str
    rankedPictureIds: list[str]

    @field_validator("rankedPictureIds")
    @classmethod
    def valid_ranking(cls, values: list[str]) -> list[str]:
        if len(values) > 100 or len(values) != len(set(values)):
            raise ValueError("ranking must be unique and contain at most 100 IDs")
        if any(not value.isdigit() or int(value) < 1 for value in values):
            raise ValueError("ranked IDs must be positive integer strings")
        return values


def evaluate(golden: list[GoldenCase], predictions: list[Prediction]) -> dict[str, float | int]:
    if not golden:
        raise ValueError("golden set must not be empty")
    by_id = {item.queryId: item for item in predictions}
    if len(by_id) != len(predictions):
        raise ValueError("prediction queryId must be unique")
    totals = {"recallAt20": 0.0, "precisionAt10": 0.0, "mrr": 0.0, "ndcgAt10": 0.0}
    returned = leaked = missing = 0
    for case in golden:
        prediction = by_id.get(case.queryId)
        ranking = prediction.rankedPictureIds if prediction else []
        if prediction is None:
            missing += 1
        relevant = set(case.relevantPictureIds)
        top20, top10 = ranking[:20], ranking[:10]
        totals["recallAt20"] += len(relevant.intersection(top20)) / len(relevant)
        totals["precisionAt10"] += len(relevant.intersection(top10)) / 10
        first = next((index for index, value in enumerate(ranking, 1) if value in relevant), None)
        totals["mrr"] += 0 if first is None else 1 / first
        dcg = sum(1 / math.log2(index + 2) for index, value in enumerate(top10) if value in relevant)
        ideal = sum(1 / math.log2(index + 2) for index in range(min(len(relevant), 10)))
        totals["ndcgAt10"] += dcg / ideal
        returned += len(ranking)
        leaked += len(set(ranking).intersection(case.forbiddenPictureIds))
    count = len(golden)
    result: dict[str, float | int] = {key: round(value / count, 6) for key, value in totals.items()}
    result.update({
        "unauthorizedLeakageRate": round(leaked / returned, 6) if returned else 0.0,
        "unauthorizedResultCount": leaked,
        "queryCount": count,
        "missingPredictionCount": missing,
    })
    return result


def load_jsonl(path: Path, model):
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(model.model_validate_json(line))
            except Exception as error:
                raise ValueError(f"invalid JSONL row {number} in {path.name}") from error
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate LabVision retrieval predictions")
    parser.add_argument("golden", type=Path)
    parser.add_argument("predictions", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(load_jsonl(args.golden, GoldenCase),
                              load_jsonl(args.predictions, Prediction)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
