from pydantic import BaseModel


class Metric(BaseModel):
    key: str
    label: str
    value: float | int
    display_value: str
    change: str
    trend: str
    icon: str


class ChartPoint(BaseModel):
    label: str
    revenue: float = 0
    expense: float = 0
    inspections: int = 0


class AlertItem(BaseModel):
    id: str
    title: str
    detail: str
    level: str
    time: str


class ActivityItem(BaseModel):
    id: str
    title: str
    detail: str
    time: str
    type: str


class DashboardResponse(BaseModel):
    scope: str
    greeting: str
    metrics: list[Metric]
    finance_chart: list[ChartPoint]
    operations_chart: list[ChartPoint]
    alerts: list[AlertItem]
    activities: list[ActivityItem]
    pending_approvals: int

