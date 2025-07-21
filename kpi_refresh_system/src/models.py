from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import date

@dataclass
class Company:
    company_id: str
    csin: str
    name: str
    ticker_canalyst: str
    sector: Optional[str] = None

@dataclass
class TimeSeries:
    slug: str
    names: List[str]
    description: str
    unit: str
    category: str
    is_kpi: bool = False

@dataclass
class DataPoint:
    time_series: str
    period_name: str
    period_type: str  # fiscal_quarter, fiscal_year
    value: Optional[float]
    start_date: date
    end_date: date

@dataclass
class Period:
    name: str  # e.g., "Q1-2025", "FY2024"
    period_duration_type: str
    start_date: date
    end_date: date