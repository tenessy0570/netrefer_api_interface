from fastapi import APIRouter

from dependencies import get_netrefer_api_client
from models import BtagStatisticsInputModel, BtagStatisticsResponseModel

router = APIRouter()


@router.post("/btag_statistics")
def register(input_data: BtagStatisticsInputModel) -> BtagStatisticsResponseModel:
    client = get_netrefer_api_client()
    return client.get_btag_statistics(
        from_=input_data.from_,
        to=input_data.to,
        btag=input_data.btag
    )
