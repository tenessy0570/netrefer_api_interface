import datetime
from decimal import Decimal

import pandas
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
        self.access_token = None

    def update_access_token(self):
        config.logger.info("Updating access token")
        url = f"https://netreferb2cprod.b2clogin.com/netreferb2cprod.onmicrosoft.com/b2c_1_si_pwd/oauth2/v2.0/token" \
              f"?client_id={self.client_id}&username={self.netrefer_username}&pas" \
              f"sword={self.netrefer_password}&grant_type=password&scope=openid offline_access " \
              f"https://netreferb2cprod.onmicrosoft.com/NetRefer.Api.Lists/Lists.Read.All "

        resp = requests.post(url)

        if resp.status_code not in (200, 201):
            raise Exception(f"An error while retrieving access token: \n{resp.text}")

        token = resp.json()["access_token"]
        self.access_token = token

    def execute(self, *args, **kwargs):
        kwargs["params"] = self.params
        kwargs["headers"] = {"Authorization": f"Bearer {self.access_token}"}

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
            take: int = 500,
            consumer_ids: list[int] = None,
            items: list = None
    ) -> list[dict]:
        if items is None:
            items = []

        config.logger.info(f"Getting deposits: {from_=}, {to=}, {skip=}, {consumer_ids=}, {limit=}")
        if limit:
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
            # THIS MIGHT SLOW THE API RESPONSE
            # "order": [
            #     {"timestamp": "DESC"}
            # ]
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
            return self.get_deposits(
                from_=from_,
                to=to,
                skip=skip + take,
                take=take,
                consumer_ids=consumer_ids,
                items=[*items, *deposits],
                limit=limit
            )

        return [*items, *deposits]

    def get_players(
            self,
            *,
            from_: datetime.datetime,
            to: datetime.datetime,
            limit: int = None,
            skip: int = 0,
            take: int = 250,
            btags: list[int] = None,
            items: list = None
    ) -> list[dict]:
        if items is None:
            items = []

        config.logger.info(f"Getting players: {skip=}, {btags=}, {limit=}")
        if limit:
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
              }
              items {
                  consumerID
                  registrationTimestamp
              }
            }
          }
        """

        variables = {
            "skip": skip,
            "take": take,
            "where": {
                "registrationTimestamp": {
                    "gte": str(from_),
                    "lte": str(to)
                }
            }
            # THIS MIGHT SLOW THE API RESPONSE
            # "order": [
            #     {"registrationTimestamp": "DESC"}
            # ]
        }

        if btags:
            variables["where"]["affiliateID"] = {"in": btags}

        resp = self.execute(query=query, variables=variables)

        try:
            data = resp["data"]["player"]
        except KeyError:
            raise Exception(resp)

        players = data["items"]
        if data["pageInfo"]["hasNextPage"]:
            return self.get_players(
                from_=from_,
                to=to,
                skip=skip + take,
                take=take,
                btags=btags,
                items=[*items, *players],
                limit=limit
            )

        return [*items, *players]

    def get_btag_statistics(
            self,
            from_: datetime.datetime,
            to: datetime.datetime,
            btag: int
    ) -> BtagStatisticsResponseModel:
        self.update_access_token()

        config.logger.info(f"Retrieving btag stats: {btag=}, {from_=}, {to=}")
        players_by_btag = self.get_players(
            from_=from_,
            to=to,
            btags=[btag]
        )

        if not players_by_btag:
            raise Exception(f"Players with btag {btag} not found.")

        config.logger.info(f"Number of players: {len(players_by_btag)}")

        registrations_count = len(players_by_btag)
        ftds_count = 0
        deposits_count = 0
        deposits_summary = Decimal('0')
        ftds_summary = Decimal('0')

        deposits = self.get_deposits(
            from_=from_,
            to=to,
            consumer_ids=[player["consumerID"] for player in players_by_btag]
        )

        df = pandas.DataFrame.from_records(deposits)
        deposits_count += len(df)

        if deposits_count == 0:
            return BtagStatisticsResponseModel(
                btag=str(btag),
                from_=from_,
                to=to,
                registrations_count=registrations_count,
                ftds_count=ftds_count,
                ftds_summary=ftds_summary,
                deposits_count=deposits_count,
                deposits_summary=deposits_summary,
            )

        for index, row in df.iterrows():
            deposits_summary += Decimal(str(row['depositAmount']))

        df_first_deposits = df.sort_values(by="timestamp").groupby("consumerID").first()
        ftds_count += len(df_first_deposits)

        for index, row in df_first_deposits.iterrows():
            ftds_summary += Decimal(str(row['depositAmount']))

        response = BtagStatisticsResponseModel(
            btag=str(btag),
            from_=from_,
            to=to,
            registrations_count=registrations_count,
            ftds_count=ftds_count,
            ftds_summary=ftds_summary,
            deposits_count=deposits_count,
            deposits_summary=deposits_summary,
        )

        # TODO: This might cause an error because sometimes round throws
        # an exception when trying to pass value of type Decimal as an first argument
        response.deposits_summary = round(response.deposits_summary, 2)
        response.ftds_summary = round(response.ftds_summary, 2)
        return response
