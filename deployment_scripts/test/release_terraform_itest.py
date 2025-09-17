import boto3
import os, sys
import unittest
import logging
import tempfile
from unittest.mock import patch
from io import StringIO
from contextlib import redirect_stderr, redirect_stdout
from moto import mock_sqs, mock_organizations, mock_sts
from deployment_scripts.release_terraform_pr import (
    main,
    MissingArgumentsException,
)


def create_test_folder(folder):
    os.mkdir(folder)


def remove_test_folder(folder):
    os.system(f"rm -rf {folder}")


@mock_sts
@mock_sqs
@mock_organizations
def setup_module():
    """ Set up required """
    version = "v0.0.0"
    os.environ["SQS_URL"] = "dummy_queue"
    os.environ["ROOT_ACCOUNT_ID"] = "112233445566"

    return


class RunReleaseTerraform(unittest.TestCase):
    environ = "testing"
    version = "v0.0.0"

    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)

    def test_no_args(self) -> None:
        """ test main function, should exit """
        with redirect_stderr(StringIO()) as err:
            with self.assertRaises(SystemExit):
                main("test_folder_name", "test_folder_name")
        self.assertIn("usage:", err.getvalue())

    def test_no_args_exit_code(self) -> None:
        """ test main function, should exit """
        with redirect_stderr(StringIO()) as err:
            with self.assertRaises(SystemExit) as e:
                main("test_folder_name", "test_folder_name")
            self.assertEqual(e.exception.code, 2)
        self.assertIn("usage:", err.getvalue())

    # @mock_sts
    # @mock_sqs
    # @mock_organizations
    # def test_release_terraform_args(self) -> None:
    #     """ test main function """
    #     setup_module()
    #     os.environ["GITHUB_API_TOKEN"] = "897654321"
    #     sqs = boto3.resource("sqs")
    #     sqs.create_queue(QueueName=os.environ["SQS_URL"])

    #     with tempfile.TemporaryDirectory() as test_folder_name:
    #         testargs = [
    #             "--base testing",
    #             "--version v0.0.0",
    #             "--project platsec-lambda-prowler-manager",
    #         ]
    #         os.system(f"touch {test_folder_name}/test.py")
    #         os.system(f"touch {test_folder_name}/test-{self.version}.zip")
    #         with patch.object(sys, "argv", testargs):
    #             main(test_folder_name, test_folder_name)
