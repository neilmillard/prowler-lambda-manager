import boto3
from typing import List, Dict, Union

Account = Dict[str, Union[str, List[int]]]


class Organisation:

    def get_organisation_accounts(self, root_account: str, max_results: int = 20) -> Dict[str, Dict[str, str]]:

        sts = boto3.client("sts")

        credentials = sts.assume_role(
            RoleArn=f"arn:aws:iam::{root_account}:role/RoleSecurityReadOnly",
            RoleSessionName="platsec_lambda_prowler_manager",
        )["Credentials"]

        organization = boto3.client(
            "organizations",
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name="eu-west-2",
        )

        accounts = {"Accounts": []}

        next_token = None
        while True:

            if next_token is None:
                payload = {"MaxResults": max_results}
            else:
                payload = {"MaxResults": max_results, "NextToken": next_token}

            response = organization.list_accounts(**payload)

            for account in response["Accounts"]:
                accounts["Accounts"].append({"Id": account["Id"], "Name": account["Name"]})

            if "NextToken" not in response:
                break
            next_token = response["NextToken"]

        return self._org_restructure(accounts)

    @staticmethod
    def _org_restructure(org_output: Dict[str, List[Account]]) -> Dict[str, Account]:
        org_data = {}
        for account in org_output["Accounts"]:
            org_data[account["Id"]] = {"Name": account["Name"]}
            if "Groups" in account:
                org_data[account["Id"]]["Groups"] = account["Groups"]
        return org_data
