import datetime
from decimal import Decimal

from pydantic import BaseModel


class BtagStatisticsResponseModel(BaseModel):
    btag: str
    from_: datetime.datetime
    to: datetime.datetime
    registrations_count: int
    ftds_count: int
    ftds_summary: Decimal
    deposits_count: int
    deposits_summary: Decimal


class BtagStatisticsInputModel(BaseModel):
    btag: str
    from_: datetime.datetime
    to: datetime.datetime

