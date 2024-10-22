import config
from api.netrefer import NetreferApiClient


def get_netrefer_api_client() -> NetreferApiClient:
    return NetreferApiClient(
        api_endpoint=config.NETREFER_API_ENDPOINT,
        api_token=config.NETREFER_API_TOKEN,
        api_subscription_key=config.NETREFER_API_SUBSCRIPTION_KEY
    )
