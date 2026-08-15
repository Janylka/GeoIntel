from dataclasses import dataclass
from enum import Enum


class Plan(str, Enum):
    TRIAL = "trial"
    FARMER = "farmer"
    FARM = "farm"
    ORG = "org"


class PlanLimitError(ValueError):
    pass


@dataclass(frozen=True)
class PlanDef:
    id: Plan
    max_fields: int | None  # None for unlimited
    price_tiyin_month: int
    features: frozenset[str]


PLANS: dict[Plan, PlanDef] = {
    Plan.TRIAL: PlanDef(
        id=Plan.TRIAL,
        max_fields=1,
        price_tiyin_month=0,
        features=frozenset(["drought_status", "weather_forecast_7d"]),
    ),
    Plan.FARMER: PlanDef(
        id=Plan.FARMER,
        max_fields=5,
        price_tiyin_month=40000,
        features=frozenset(
            ["drought_status", "weather_forecast_7d", "season_history", "email_alerts"]
        ),
    ),
    Plan.FARM: PlanDef(
        id=Plan.FARM,
        max_fields=50,
        price_tiyin_month=250000,
        features=frozenset(
            [
                "drought_status",
                "weather_forecast_7d",
                "season_history",
                "email_alerts",
                "yield_forecast",
                "data_export",
            ]
        ),
    ),
    Plan.ORG: PlanDef(
        id=Plan.ORG,
        max_fields=None,
        price_tiyin_month=2000000,
        features=frozenset(
            [
                "drought_status",
                "weather_forecast_7d",
                "season_history",
                "email_alerts",
                "yield_forecast",
                "data_export",
                "full_district_access",
            ]
        ),
    ),
}


def can_use(plan: Plan, feature: str) -> bool:
    return feature in PLANS[plan].features


def assert_field_limit(plan: Plan, current_count: int) -> None:
    plan_def = PLANS[plan]
    if plan_def.max_fields is not None and current_count >= plan_def.max_fields:
        raise PlanLimitError(f"Plan '{plan.value}' limit of {plan_def.max_fields} fields reached.")
