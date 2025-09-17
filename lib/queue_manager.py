
import json
import boto3
from typing import List, Dict, Union
from botocore.exceptions import BotoCoreError, ClientError

Account = Dict[str, Union[str, List[int]]]


class QueueException(Exception):
    pass


class QueueManager:

    def send_to_sqs(self, queue_url: str, accounts_with_configs: Dict[str, List[Account]]) -> bool:

        try:
            sqs = boto3.client("sqs", "eu-west-2")
            count_msgs_sent = 0
            msg_ids = []
            for account_id in accounts_with_configs.keys():
                data = {"Id": account_id, "Name": accounts_with_configs[account_id]["Name"], "Groups": []}
                if "Groups" in accounts_with_configs[account_id]:
                    data["Groups"] = accounts_with_configs[account_id]["Groups"]

                response = sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(data))
                msg_ids.append(response['MessageId'])
                count_msgs_sent = count_msgs_sent + 1

            return True
        except (BotoCoreError, ClientError) as e:
            raise QueueException(f"unable to send message to queue {queue_url}") from e
