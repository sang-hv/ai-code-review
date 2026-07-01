from typing import Protocol

from argus_review.services.cost.schema import CostReportSchema, CalculateCostSchema


class CostServiceProtocol(Protocol):
    def calculate(self, result: CalculateCostSchema) -> CostReportSchema | None:
        ...

    def aggregate(self) -> CostReportSchema | None:
        ...
