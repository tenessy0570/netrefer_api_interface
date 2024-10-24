import datetime
import logging
from decimal import Decimal

import requests
from python_graphql_client import GraphqlClient
from requests.exceptions import HTTPError

import config
from models import BtagStatisticsResponseModel


class NetreferApiClient:
    def __init__(
            self,
            api_endpoint: str,
            client_id: str,
            api_subscription_key: str,
            netrefer_username: str,
            netrefer_password
    ):
        self.api_endpoint = api_endpoint
        self.client = GraphqlClient(endpoint=config.NETREFER_API_ENDPOINT)
        self.client_id = client_id
        self.netrefer_username = netrefer_username
        self.netrefer_password = netrefer_password
        self.params = {"subscription-key": api_subscription_key}

    def get_access_token(self) -> str:
        url = f"https://netreferb2cprod.b2clogin.com/netreferb2cprod.onmicrosoft.com/b2c_1_si_pwd/oauth2/v2.0/token" \
              f"?client_id={self.client_id}&username={self.netrefer_username}&pas" \
              f"sword={self.netrefer_password}&grant_type=password&scope=openid offline_access " \
              f"https://netreferb2cprod.onmicrosoft.com/NetRefer.Api.Lists/Lists.Read.All "

        resp = requests.post(url)

        if resp.status_code not in (200, 201):
            raise Exception(f"An error while retrieving access token: \n{resp.text}")

        return resp.json()["access_token"]

    def execute(self, *args, **kwargs):
        """
        Create new access token each time we do a request. Doing it just in case so
        token is always actual.
        """
        access_token = self.get_access_token()

        kwargs["params"] = self.params
        kwargs["headers"] = {"Authorization": f"Bearer {access_token}"}

        try:
            result = self.client.execute(*args, **kwargs)
        except HTTPError as exc:
            raise Exception(str(exc))

        return result

    def get_deposits(
            self,
            *,
            from_: datetime.datetime,
            to: datetime.datetime,
            limit: int = None,
            skip: int = 0,
            take: int = 400,
            consumer_ids: list[int] = None,
            items: list = None
    ) -> list[dict]:
        if items and limit:
            if len(items) >= limit:
                return items

        query = """
          query Deposit(
            $skip: Int
            $take: Int
            $where: DepositFilterInput
            $order: [DepositSortInput!]
          ) {
            deposit(
              skip: $skip
              take: $take
              where: $where
              order: $order
            ) {
              pageInfo {
                hasNextPage
                hasPreviousPage
              }
              items {
                consumerID
                depositAmount
                brandID
                consumerCurrencyID
                timestamp
              }
              totalCount
            }
          }
        """

        variables = {
            "skip": skip,
            "take": take,
            "where": {
                # "consumerID": {"eq": 191936},
                "timestamp": {
                    "gte": str(from_),
                    "lte": str(to)
                }
            },
            "order": [
                {"timestamp": "DESC"}
            ]
        }

        if consumer_ids:
            variables["where"]["consumerID"] = {"in": consumer_ids}

        resp = self.execute(query=query, variables=variables)

        try:
            data = resp["data"]["deposit"]
        except KeyError:
            raise Exception(resp)

        deposits = data["items"]
        if data["pageInfo"]["hasNextPage"]:
            if not items:
                items = []

            return self.get_deposits(
                from_=from_,
                to=to,
                skip=skip + take,
                take=take,
                consumer_ids=consumer_ids,
                items=[*items, *deposits],
                limit=limit
            )

        return deposits

    def get_players(
            self,
            *,
            limit: int = None,
            skip: int = 0,
            take: int = 400,
            btags: list[str] = None,
            items: list = None
    ) -> list[dict]:
        if items and limit:
            if len(items) >= limit:
                return items

        query = """
          query Player(
            $skip: Int
            $take: Int
            $where: PlayerFilterInput
            $order: [PlayerSortInput!]
          ) {
            player(
              skip: $skip
              take: $take
              where: $where
              order: $order
            ) {
              pageInfo {
                hasNextPage
                hasPreviousPage
              }
              items {
                  consumerID
                  registrationTimestamp
                  bTag
                  consumerCountry
                  consumerState
                  username
                  brandID
                  consumerCurrencyID
                  consumerStatus
                  affiliateID
                  source
                  rewardPlanID
                  customerTypeID
                  cpaProcessed
                  expired
                  lastUpdated
              }
              totalCount
            }
          }
        """

        variables = {
            "skip": skip,
            "take": take,
            "order": [
                {"registrationTimestamp": "DESC"}
            ]
        }

        if btags:
            variables["where"] = {
                "bTag": {"in": btags}
            }

        resp = self.execute(query=query, variables=variables)

        try:
            data = resp["data"]["player"]
        except KeyError:
            raise Exception(resp)

        players = data["items"]
        if data["pageInfo"]["hasNextPage"]:
            if not items:
                items = []

            return self.get_players(
                skip=skip + take,
                take=take,
                btags=btags,
                items=[*items, *players],
                limit=limit
            )

        return players

    def get_btag_statistics(
            self,
            from_: datetime.datetime,
            to: datetime.datetime,
            btag: str
    ) -> BtagStatisticsResponseModel:
        players_by_btag = self.get_players(
            btags=[btag]
        )

        if not players_by_btag:
            raise Exception(f"Player with btag {btag} not found.")

        consumer_id: int = players_by_btag[0]["consumerID"]
        registration_timestamp = players_by_btag[0]["registrationTimestamp"]

        deposits = self.get_deposits(
            from_=from_,
            to=to,
            consumer_ids=[consumer_id]
        )

        response = BtagStatisticsResponseModel(
            btag=btag,
            from_=from_,
            to=to,
            registrations_count=0 if not registration_timestamp else 1,
            ftds_count=0 if not deposits else 1,
            ftds_summary=Decimal(deposits[0]['depositAmount']) if deposits else Decimal('0'),
            deposits_count=len(deposits),
            deposits_summary=sum([Decimal(deposit['depositAmount']) for deposit in deposits])
        )

        # TODO: This might cause an error because sometimes round throws
        # an exception when trying to pass value of type Decimal as an first argument
        response.deposits_summary = round(response.deposits_summary, 2)
        response.ftds_summary = round(response.ftds_summary, 2)
        return response
