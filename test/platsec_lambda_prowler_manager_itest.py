import os
import unittest
import boto3
import logging
from moto import mock_sqs, mock_organizations, mock_sts
from unittest import mock
from typing import List, Dict
from lib.config import ParameterException, ConfigFileException
from lib.account_prowler_groups import Account
from platsec_lambda_prowler_manager import handler


@mock_sts
@mock_sqs
@mock_organizations
class RunPlatsecLambdaProwlermanager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)

    @mock.patch.dict(
        os.environ,
        {"SQS_URL": "the_queue_to_use", "ROOT_ACCOUNT_ID": "123456789012"},
    )
    @mock.patch("platsec_lambda_prowler_manager.boto3.client")
    @mock_sts
    @mock_sqs
    @mock_organizations
    def test_success(self, mock_client) -> None:
        sqs = boto3.resource("sqs", "eu-west-2")
        sqs.create_queue(QueueName=os.environ["SQS_URL"])
        config_file = f"test/fixtures/{unittest.TestCase.id(self)}.input.json"
        org_input: Dict[str, List[Account]] = {
            "Accounts": [
                {"Id": "123456789012", "Name": "this account"},
                {"Id": "091508262615", "Name": "other"},
            ]
        }

        client = mock_client.return_value
        client.list_accounts.return_value = {"Accounts": org_input["Accounts"]}
        want = "ok"
        payload = {"config_file": config_file}
        got = handler(payload, 1)
        self.assertEqual(want, got)

    @mock.patch.dict(
        os.environ,
        {"SQS_URL": "the_queue_to_use", "ROOT_ACCOUNT_ID": "123456789012"},
    )
    @mock_sts
    @mock_sqs
    @mock_organizations
    def test_missing_config_file_parameter(self) -> None:
        sqs = boto3.resource("sqs", "eu-west-2")
        sqs.create_queue(QueueName=os.environ["SQS_URL"])
        payload = {}
        with self.assertRaises(ConfigFileException):
            handler(payload, 1)

    @mock.patch.dict(os.environ, {"ROOT_ACCOUNT_ID": "123456789012"})
    @mock_sts
    @mock_sqs
    @mock_organizations
    def test_missing_queue_name_parameter(self) -> None:
        config_file = f"test/fixtures/{unittest.TestCase.id(self)}.input.json"
        payload = {"config_file": config_file}
        with self.assertRaises(ParameterException):
            handler(payload, 1)

    @mock.patch.dict(os.environ, {"SQS_URL": "the_queue_to_use"})
    @mock_sts
    @mock_sqs
    @mock_organizations
    def test_missing_root_account_parameter(self) -> None:
        config_file = f"test/fixtures/{unittest.TestCase.id(self)}.input.json"
        payload = {"config_file": config_file}
        with self.assertRaises(ParameterException):
            handler(payload, 1)


if __name__ == "__main__":
    unittest.main()
