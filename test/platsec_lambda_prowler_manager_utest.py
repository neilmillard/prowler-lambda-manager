import os
import unittest
import boto3
import json
from moto import mock_sqs, mock_sts
from unittest import mock
from typing import List, Dict
from data.exceptions import GetAccountConfigsException
from lib.organisation_manager import Organisation
from lib.account_prowler_groups import AccountProwlerGroups, Account
from lib.queue_manager import QueueManager, QueueException


@mock_sts
def create_mock_session(account_id: str, role_name: str, session_name: str) -> dict:
    sts = boto3.client("sts")
    session = sts.assume_role(RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}", RoleSessionName=session_name)
    return session


def get_content(file: str) -> str:
    with open(file, "r") as f:
        return f.read()


class TestConvertAmazonOrgFormatToConfigFormat(unittest.TestCase):
    org = Organisation()

    def test_success_with_groups(self):
        org_input: Dict[str, List[Account]] = {
            "Accounts": [
                {"Id": "123456789012", "Name": "this account", "Groups": [1, 2, 3]},
                {"Id": "091508262615", "Name": "other", "Groups": [1, 2, 3]},
            ]
        }
        want = {
            "123456789012": {"Name": "this account", "Groups": [1, 2, 3]},
            "091508262615": {"Name": "other", "Groups": [1, 2, 3]},
        }

        got = self.org._org_restructure(org_input)
        self.assertEqual(got, want)

    def test_success_without_groups(self):
        org_input: Dict[str, List[Account]] = {
            "Accounts": [
                {"Id": "123456789012", "Name": "this account"},
                {"Id": "091508262615", "Name": "other"},
            ]
        }
        want = {
            "123456789012": {"Name": "this account"},
            "091508262615": {"Name": "other"},
        }

        got = self.org._org_restructure(org_input)
        self.assertEqual(got, want)


class TestGetOrganizationAccounts(unittest.TestCase):
    maxDiff = None
    org = Organisation()

    @mock_sts
    @mock.patch("platsec_lambda_prowler_manager.boto3.client")
    def test_success_without_pagination(self, mock_client):
        org_input: Dict[str, List[Account]] = {
            "Accounts": [
                {"Id": "123456789012", "Name": "this account"},
                {"Id": "091508262615", "Name": "other"},
            ]
        }
        want = self.org._org_restructure(org_input)
        root_account_id = "123456789012"

        client = mock_client.return_value
        client.list_accounts.return_value = {"Accounts": org_input["Accounts"]}

        got = self.org.get_organisation_accounts(root_account_id)

        self.assertEqual(got, want)

    @mock_sts
    @mock.patch("platsec_lambda_prowler_manager.boto3.client")
    def test_success_with_pagination(self, mock_client):
        org_input: Dict[str, List[Account]] = {
            "Accounts": [
                {"Id": "123456789012", "Name": "this account"},
                {"Id": "091508262615", "Name": "other"},
            ],
        }
        want = self.org._org_restructure(org_input)
        root_account_id = "123456789012"

        client = mock_client.return_value
        client.list_accounts.side_effect = [
            {"Accounts": [org_input["Accounts"][0]], "NextToken": "token"},
            {"Accounts": [org_input["Accounts"][1]]},
        ]

        got = self.org.get_organisation_accounts(root_account_id, max_results=1)

        self.assertEqual(got, want)


class TestGetAccountProwlerChecks(unittest.TestCase):
    apg = AccountProwlerGroups()

    def test_success(self) -> None:
        config_file = f"test/fixtures/{unittest.TestCase.id(self)}.input.json"
        accounts = json.loads(get_content("test/fixtures/accounts.input.json"))
        want = json.loads(get_content(f"test/fixtures/{unittest.TestCase.id(self)}.want.json"))

        got = self.apg.get_account_prowler_groups(accounts, config_file)

        self.assertEqual(got, want)

    def test_account_missing_from_config(self) -> None:
        config_file = f"test/fixtures/{unittest.TestCase.id(self)}.input.json"
        want = json.loads(get_content(f"test/fixtures/{unittest.TestCase.id(self)}.want.json"))
        accounts = json.loads(get_content("test/fixtures/accounts.input.json"))
        got = self.apg.get_account_prowler_groups(accounts, config_file)
        self.assertEqual(got, want)

    def test_config_file_missing(self) -> None:
        config_file = "test/fixtures/no_file.json"
        accounts = json.loads(get_content("test/fixtures/accounts.input.json"))
        with self.assertRaises(GetAccountConfigsException):
            self.apg.get_account_prowler_groups(accounts, config_file)

    def test_invalid_json_config_file(self) -> None:
        config_file = f"test/fixtures/{unittest.TestCase.id(self)}.input.json"
        accounts = json.loads(get_content("test/fixtures/accounts.input.json"))
        with self.assertRaises(GetAccountConfigsException):
            self.apg.get_account_prowler_groups(accounts, config_file)

    def test_config_file_invalid_check_entry(self) -> None:
        config_file = f"test/fixtures/{unittest.TestCase.id(self)}.input.json"
        accounts = json.loads(get_content("test/fixtures/accounts.input.json"))
        with self.assertRaises(GetAccountConfigsException):
            self.apg.get_account_prowler_groups(accounts, config_file)

    def test_config_file_invalid_account(self) -> None:
        config_file = f"test/fixtures/{unittest.TestCase.id(self)}.input.json"
        accounts = json.loads(get_content("test/fixtures/accounts.input.json"))
        with self.assertRaises(GetAccountConfigsException):
            self.apg.get_account_prowler_groups(accounts, config_file)


class TestQueueManager(unittest.TestCase):
    sqs_service = QueueManager()

    @mock.patch.dict(os.environ, {"SQS_URL": "the_queue_to_use"})
    @mock_sqs
    def test_success(self) -> None:
        sqs = boto3.resource("sqs", "eu-west-2")
        sqs.create_queue(QueueName=os.environ["SQS_URL"])
        want = True
        with open(f"test/fixtures/accounts_with_configs.json") as accounts_data:
            dummy_account_configs = json.load(accounts_data)
            got = self.sqs_service.send_to_sqs(os.environ["SQS_URL"], dummy_account_configs)

        self.assertEqual(want, got)

    @mock.patch.dict(os.environ, {"SQS_URL": "the_queue_to_use"})
    @mock_sqs
    def test_check_sqs_message(self) -> None:
        sqs = boto3.resource("sqs", "eu-west-2")
        queue = sqs.create_queue(QueueName=os.environ["SQS_URL"])
        want_msg = '{"Id": "123456789012", "Name": "account-one", "Groups": [1, 3]}'
        with open(f"test/fixtures/{unittest.TestCase.id(self)}.input.json") as accounts_data:
            dummy_account_configs = json.load(accounts_data)
            self.sqs_service.send_to_sqs(os.environ["SQS_URL"], dummy_account_configs)
            sqs_messages = queue.receive_messages()
            got_msg = sqs_messages[0].body
        self.assertEqual(len(sqs_messages), 1, "should send one message")
        self.assertEqual(want_msg, got_msg)

    @mock.patch.dict(os.environ, {"SQS_URL": "the_queue_to_use"})
    @mock_sqs
    def test_queue_manager_no_queue(self) -> None:
        with open(f"test/fixtures/accounts_with_configs.json") as accounts_data:
            dummy_account_configs = json.load(accounts_data)
            with self.assertRaises(QueueException):
                self.sqs_service.send_to_sqs(os.environ["SQS_URL"], dummy_account_configs)

    @mock.patch.dict(os.environ, {"SQS_URL": "the_queue_to_use"})
    @mock_sqs
    def test_queue_manager_wrong_name(self) -> None:
        sqs = boto3.resource("sqs", "eu-west-2")
        sqs.create_queue(QueueName="name-of-queue")
        with open(f"test/fixtures/accounts_with_configs.json") as accounts_data:
            dummy_account_configs = json.load(accounts_data)
            with self.assertRaises(QueueException):
                self.sqs_service.send_to_sqs(os.environ["SQS_URL"], dummy_account_configs)
