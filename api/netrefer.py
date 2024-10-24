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

    def get_deposits(
            self,
            from_: datetime.datetime,
            to: datetime.datetime,
            skip: int = 0,
            take: int = 400,
            consumer_ids: list[int] = None,
            items: list = None
    ) -> dict:
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
        }

        if consumer_ids:
            variables["where"]["consumerId"] = {"in": consumer_ids}

        resp = self.execute(query=query, variables=variables)

        try:
            data = resp["data"]
        except KeyError:
            raise Exception(resp)

        deposits = data["deposit"]["items"]
        if not data["pageInfo"]["hasNextPage"]:
            if not items:
                items = []

            return self.get_deposits(
                from_=from_,
                to=to,
                skip=skip + take,
                take=take,
                consumer_ids=consumer_ids,
                items=[*items, *deposits]
            )

        return deposits

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

    def get_btag_statistics(
            self,
            from_: datetime.datetime,
            to: datetime.datetime,
            btag: str
    ) -> BtagStatisticsResponseModel:
        players_query = """
            query playersQuery($countryCode: String) {
                player($skip: Int, $take: Int, $where: PlayerFilterInput, $order: [PlayerSortInput!]) {
                    PlayerCollectionSegment {
                        Player {
                              consumerID
                              bTag
                              registrationTimestamp
                        }
                    }
                }
            }
        """

        variables = {
            "skip": 0,
            "take": 800,
            "where": None,
            "order": None
        }

        data = self.execute(query=players_query, variables=variables)

        try:
            items = data["data"]["PlayerCollectionSegment"]["items"]
        except KeyError:
            raise Exception(data)

        consumer_id: int = None
        registration_timestamp = None

        for player in items:
            if player["bTag"] != btag:
                continue

            consumer_id = int(player["consumerID"])
            registration_timestamp = player["registrationTimestamp"]

        if consumer_id is None:
            raise Exception(f"Player with btag {btag} not found.")

        deposits_query = """
            query depositsQuery($countryCode: String) {
                deposit($skip: Int, $take: Int, $where: DepositFilterInput, $order: [DepositSortInput!]) {
                    DepositCollectionSegment {
                        Deposit {
                              consumerID
                              depositAmount
                              brandID
                              consumerCurrencyID
                              timestamp
                        }
                    }
                }
            }
        """

        variables = {
            "skip": 0,
            "take": 800,
            "where": """
                {
                    and: [
                        {
                          consumerID: {consumer_id}
                        },
                        {
                          timestamp: {"lte": {to}} 
                        },
                        {
                          timestamp: {"gte": {from_}}
                        },
                    ]
                }

            """.format(consumer_id=consumer_id, to=to, from_=from_),
            "order": """
                {
                    timestamp: "ASC"
                }
            """
        }

        data = self.execute(query=deposits_query, variables=variables)

        try:
            items = data["data"]["DepositCollectionSegment"]["items"]
        except KeyError:
            raise Exception(data)

        response = BtagStatisticsResponseModel(
            btag=btag,
            from_=from_,
            to=to,
            registrations_count=0 if not registration_timestamp else 1,
            ftds_count=0 if not items else 1,
            ftds_summary=Decimal(items[0]['depositAmount']) if items else Decimal('0'),
            deposits_count=len(items),
            deposits_summary=sum([Decimal(deposit['depositAmount']) for deposit in items])
        )

        return response
