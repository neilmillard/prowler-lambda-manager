import json
from os import path
from typing import List, Dict, Union
from data.exceptions import *


Account = Dict[str, Union[str, List[int]]]


class AccountProwlerGroups:

    def get_account_prowler_groups(self, accounts: Dict[str, Dict[str, str]], config_file_path: str) -> Dict[str, List[Account]]:

        if not path.isfile(config_file_path):
            raise GetAccountConfigsException(f"unable to locate file at {config_file_path}")

        with open(config_file_path, "r") as f:
            try:
                config = json.load(f)
            except Exception as e:
                raise GetAccountConfigsException(f"unable to read {config_file_path}") from e

        for config_account_id in config.keys():
            if config_account_id not in accounts.keys():
                raise GetAccountConfigsException(f"unable to find {config_account_id} in organisation")

        for account_id in accounts.keys():
            if account_id in config:
                if "Groups" in config[account_id]:
                    for item in config[account_id]["Groups"]:
                        if not type(item) is int:
                            raise GetAccountConfigsException(f"item {item} is invalid type in {config_file_path}")

                    accounts[account_id]["Groups"] = config[account_id]["Groups"]

        return accounts
