
import os
from typing import List, Dict, Union
from botocore.exceptions import BotoCoreError, ClientError

Account = Dict[str, Union[str, List[int]]]


class ParameterException(Exception):
    pass


class ConfigFileException(Exception):
    pass


class Config:

    def __init__(self, event) -> None:
        if "ROOT_ACCOUNT_ID" not in os.environ:
            raise ParameterException("missing environment variable 'ROOT_ACCOUNT_ID'")

        if "SQS_URL" not in os.environ:
            raise ParameterException("missing environment variable 'SQS_URL'")

        if "config_file" not in event:
            raise ConfigFileException("missing parameter 'config_file'")
