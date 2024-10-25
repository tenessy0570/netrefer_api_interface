import logging

from fastapi import APIRouter, HTTPException

from dependencies import get_netrefer_api_client
from models import BtagStatisticsInputModel, BtagStatisticsResponseModel

router = APIRouter()


@router.post("/btag_statistics")
def register(input_data: BtagStatisticsInputModel) -> BtagStatisticsResponseModel:
    client = get_netrefer_api_client()

    try:
        result = client.get_btag_statistics(
            from_=input_data.from_,
            to=input_data.to,
            btag=int(input_data.btag)
        )
    except Exception as exc:
        logging.error(exc)

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    return result
