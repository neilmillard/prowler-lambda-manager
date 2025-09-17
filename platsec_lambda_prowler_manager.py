
import logging
import os
import os.path
import boto3
from typing import Dict
from lib.queue_manager import QueueManager as QM
from lib.config import Config
from lib.organisation_manager import Organisation as ORG
from lib.account_prowler_groups import AccountProwlerGroups as APG


logging.basicConfig(format="%(levelname)s:%(message)s")


def handler(event: Dict, context) -> None:
    Config(event)
    QM().send_to_sqs(
        os.environ["SQS_URL"].strip(),
        APG().get_account_prowler_groups(
            ORG().get_organisation_accounts(os.environ["ROOT_ACCOUNT_ID"].strip()),
            event["config_file"]
        )
    )

    return "ok"
