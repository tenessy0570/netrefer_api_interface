import datetime
from decimal import Decimal

from python_graphql_client import GraphqlClient

import config
from models import BtagStatisticsResponseModel


class NetreferApiClient:
    def __init__(self, api_endpoint: str, api_token: str):
        self.api_endpoint = api_endpoint
        self.api_token = api_token
        self.client = GraphqlClient(endpoint=config.NETREFER_API_ENDPOINT)
        self.headers = {"Authorization": f"Bearer {api_token}"}

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

        data = self.client.execute(query=players_query, variables=variables, headers=self.headers)

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

        data = self.client.execute(query=deposits_query, variables=variables, headers=self.headers)

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
