import config
from api.netrefer import NetreferApiClient


def get_netrefer_api_client() -> NetreferApiClient:
    return NetreferApiClient(
        api_endpoint=config.NETREFER_API_ENDPOINT,
        client_id=config.NETREFER_CLIENT_ID,
        api_subscription_key=config.NETREFER_API_SUBSCRIPTION_KEY,
        netrefer_password=config.NETREFER_PASSWORD,
        netrefer_username=config.NETREFER_USERNAME
    )
