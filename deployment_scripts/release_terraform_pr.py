#!/usr/bin/env python3

import argparse
import logging
import os
import re
import subprocess
import sys
import json
import tempfile
from dataclasses import dataclass
from os.path import abspath, dirname
from typing import Dict, List
import requests
import semantic_version

logging.basicConfig(format="%(levelname)s:%(message)s")

src_file = "../platsec_lambda_prowler_manager.py"


class InvalidSemverException(Exception):
    pass


class MissingFileException(Exception):
    pass


class MissingArtifactException(Exception):
    pass


class MissingArgumentsException(Exception):
    pass


class InvalidGitBranchException(Exception):
    pass


class GetEnvException(Exception):
    pass


class GitBranchException(Exception):
    pass


class GitCloneException(Exception):
    pass


class GitCheckoutException(Exception):
    pass


class GitCommitException(Exception):
    pass


class GitDiffException(Exception):
    pass


class GitPushException(Exception):
    pass


class GitPullRequestException(Exception):
    pass


@dataclass
class Git:
    """Git(Hub) helpers"""

    user: str
    token: str
    repo_directory: str
    org: str = "hmrc"
    repository: str = "platsec-terraform"

    def clone(self) -> None:
        output = subprocess.run(
            args=[
                "git",
                "clone",
                f"https://{self.user}:{self.token}@github.com/{self.org}/{self.repository}.git",
                self.repo_directory,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        if output.returncode != 0:
            raise GitCloneException(f"failed to clone: {output.stdout.decode('utf-8')}")

    def checkout(self, branch: str) -> None:

        output = subprocess.run(
            args=["git", "checkout", branch],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self.repo_directory,
        )

        if output.returncode != 0:
            raise GitCheckoutException(
                f"failed to checkout: {output.stdout.decode('utf-8')}"
            )

    def branch(self, name: str, base: str) -> None:

        output = subprocess.run(
            args=["git", "branch", name, base],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self.repo_directory,
        )
        if output.returncode != 0:
            raise GitBranchException(
                f"failed to branch: {output.stdout.decode('utf-8')}"
            )

    def push(self, branch: str) -> None:
        output = subprocess.run(
            args=["git", "push", "--set-upstream", "origin", branch],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self.repo_directory,
        )
        if output.returncode != 0:
            raise GitPushException(f"failed to push: {output.stdout.decode('utf-8')}")

    def commit(self, version: str) -> None:
        output = subprocess.run(
            args=[
                "git",
                "commit",
                "-S",
                "-am",
                f"auto-generated commit for version {version}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self.repo_directory,
        )
        if output.returncode != 0:
            raise GitCommitException(
                f"failed to commit: {output.stdout.decode('utf-8')}"
            )

    def are_files_changed(self) -> bool:
        output = subprocess.run(
            args=["git", "diff", "--quiet", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self.repo_directory,
        )
        if output.returncode == 0:
            return False
        if output.returncode == 1:
            return True

        raise GitDiffException(
            f"failed to check changes: {output.stdout.decode('utf-8')}"
        )

    def api_pr_url(self) -> str:
        return f"https://api.github.com/repos/{self.org}/{self.repository}/pulls"

    def headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
        }

    def pull_request_exists(self, branch: str, base: str) -> bool:
        url = f"{self.api_pr_url()}?base={base}&head={branch}"
        try:
            response = requests.request(
                method="GET",
                url=url,
                headers=self.headers(),
            )
            response.raise_for_status()
            if response.json():
                return True
        except requests.RequestException as err:
            raise GitPullRequestException(f"cannot get response from {url} ") from err
        return False

    def pull_request(self, branch: str, base: str) -> str:
        data = '{"title":"PR created by Codebuild for Prowler code release", "head": "'+branch+'", "base": "'+base+'"}'
        try:
            response = requests.post(
                self.api_pr_url(),
                headers=self.headers(),
                data=data
            )
            response.raise_for_status()
            response.json()["html_url"]
            return response.json()["html_url"]
        except requests.RequestException as err:
            raise GitPullRequestException(
                f"cannot send request to {self.api_pr_url()} with payload: {data}"
            ) from err


@dataclass
class CliArguments:

    project: str
    version: str
    base: str


def main(src_dir, build_dir) -> None:
    arguments = parse_arguments(sys.argv[1:])
    runtime = get_python_version(
        f"{dirname(dirname(abspath(__file__)))}/.python-version"
    )
    check_artifacts(src_dir, build_dir, arguments.version)
    update_terraform_repository(arguments.base, arguments.version, runtime)


def parse_arguments(args: List[str]) -> CliArguments:
    parser = argparse.ArgumentParser(
        description="Make pull request for given release of this AWS Lambda function in PlatSec terraform repository."
    )
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="name of project or repository, eg. platsec-lambda-prowler-manager",
    )
    parser.add_argument(
        "--version",
        type=valid_version,
        required=True,
        help="full version name, eg. v1.1.1",
    )
    parser.add_argument(
        "--base",
        type=str,
        required=True,
        choices=["production", "sandbox", "development", "testing"],
        help="name of base branch against pull request will be raised",
    )

    parsed = parser.parse_args(args)
    return CliArguments(
        project=parsed.project, version=parsed.version, base=parsed.base
    )


def valid_version(arg_version: str) -> str:
    if not semantic_version.validate(arg_version.replace("v", "")):
        raise argparse.ArgumentTypeError(
            "invalid format of version, only semantic ersion format is accepted"
        )
    return arg_version


def update_terraform_repository(base: str, version: str, runtime: str) -> None:
    with tempfile.TemporaryDirectory() as directory:
        git = Git(
            user=getenv_or_raise("GITHUB_API_USER"),
            token=getenv_or_raise("GITHUB_API_TOKEN"),
            repo_directory=directory,
        )
        branch = branch_name(base, version)
        if git.pull_request_exists(branch, base):

            logging.info(
                f"nothing to do, there is already PR for branch: {branch} to base branch: development"
            )
            return

        git.clone()
        git.checkout(base)
        git.branch(branch, base)
        git.checkout(branch)
        update_runtime(runtime, f"{directory}/components/lambdas/component_vars.tf")
        update_package_version(version, f"{directory}/components/lambdas/component_vars.tf")
        if not git.are_files_changed():
            logging.info("no changes detected")
            return
        git.commit(f"updating to version {version}")
        git.push(branch)
        pr_url = git.pull_request(branch, base)
        logging.info(f"pull request successfully created: {pr_url}")
        return


def getenv_or_raise(env_name: str) -> str:
    env = os.getenv(env_name, "").strip()
    if not env:
        raise GetEnvException(f"{env_name} environment variable is not set")
    return env


def branch_name(base: str, version: str) -> str:
    """ nice name for the new branch """
    return f"{base}-{version}"


def update_runtime(runtime: str, varfile: str) -> None:
    """ update runtime  """

    with open(varfile, "r") as f:
        content = f.read()

    prowler_re = re.compile(
        r'variable ["]*prowler_scanner_lambda_runtime["]* {.*}', re.DOTALL
    )
    stuff = re.findall(prowler_re, content)[0]

    if re.search(r'default\s+= "python(.+?)', stuff):
        new_stuff = re.sub(r"\"python(.+?)\"", f'"python{runtime}"', stuff)
    else:
        new_stuff = re.sub(r"}", f'  default     = "python{runtime}"\n' + "}", stuff)

    content = content.replace(stuff, new_stuff)

    with open(varfile, "w") as f:
        f.write(content)


def update_package_version(version: str, varfile: str) -> None:
    """ update package version """

    with open(varfile, "r") as f:
        content = f.read()

    prowler_re = re.compile(
        r'variable ["]*prowler_runner_lambda_artifact_key["]* {.*}', re.DOTALL
    )
    stuff = re.findall(prowler_re, content)[0]

    if re.search(r'default\s+= "platsec-lambda-prowler-manager-.+\.zip"', stuff):
        new_stuff = re.sub(
            r'"platsec-lambda-prowler-manager-.+\.zip"', f'"platsec-lambda-prowler-manager-{version}.zip"', stuff
        )
    else:
        new_stuff = re.sub(
            r"}", f'  default     = "platsec-lambda-prowler-manager-{version}.zip"\n' + "}", stuff
        )

    content = content.replace(stuff, new_stuff)

    with open(varfile, "w") as f:
        f.write(content)


def get_python_version(file: str) -> str:
    if not os.path.isfile(file):
        raise MissingFileException(f"Unable to locate python version file at {file}")

    with open(file, "r") as f:
        python_version = f.readline().strip()

    if not semantic_version.validate(python_version):
        raise InvalidSemverException(
            "Invalid version format. Should be inline with SemVer spec - see https://semver.org"
        )
    lambda_python_version = semantic_version.Version(python_version)
    return f"{lambda_python_version.major}.{lambda_python_version.minor}"


def check_artifacts(source_file: str, target: str, version: str) -> bool:
    """ check if the zip artifacts exist """

    filename = source_file.replace("_", "-")
    filename = filename.replace("../", "")
    zip_suffix = f"-{version}.zip"
    filename = filename.replace(".py", zip_suffix)
    if os.path.isfile(f"{target}/{filename}"):
        return True
    else:
        raise MissingArtifactException(f"Missing artifact - {target}/{filename}")


if __name__ == "__main__":
    main(
        src_file,
        dirname(dirname(abspath(__file__))) + "/build-target",
    )
