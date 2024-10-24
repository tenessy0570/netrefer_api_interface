import logging
import os


logger = logging.getLogger()
logger.setLevel(level=logging.DEBUG)

NETREFER_API_ENDPOINT = os.getenv("NETREFER_API_ENDPOINT", "http://api.netrefer.com/api/list/v1")
NETREFER_CLIENT_ID = os.getenv("NETREFER_CLIENT_ID", "")
NETREFER_USERNAME = os.getenv("NETREFER_USERNAME", "")
NETREFER_PASSWORD = os.getenv("NETREFER_PASSWORD", "")
NETREFER_API_SUBSCRIPTION_KEY = os.getenv("NETREFER_API_SUBSCRIPTION_KEY", "")
