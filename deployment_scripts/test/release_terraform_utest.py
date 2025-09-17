import json
import logging
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import httpretty
from deployment_scripts.release_terraform_pr import (
    GetEnvException,
    GitBranchException,
    GitCheckoutException,
    GitCloneException,
    GitCommitException,
    GitDiffException,
    Git,
    GitPullRequestException,
    GitPushException,
    InvalidSemverException,
    MissingArtifactException,
    MissingFileException,
    CliArguments,
    check_artifacts,
    branch_name,
    get_python_version,
    getenv_or_raise,
    parse_arguments,
    update_terraform_repository,
    update_package_version,
    update_runtime
)


class TestReleaseTerraform(unittest.TestCase):
    environ = "testing"
    version = "v0.0.0"
    test_folder_name = "/tmp/testing"
    repo_name = "this-repo"
    branch = "the-branch"
    base_branch = "base-branch"
    runtime = "3.8.3"
    app_path = os.getcwd()
    git_api_base_url = "https://api.github.com/repos"

    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)

    def test_create_branch_name_check_type(self) -> None:
        """   should return string   """
        got = branch_name(self.environ, self.version)
        self.assertTrue(type(got) is str)

    def test_create_branch_name(self) -> None:
        """   should return string   """
        got = branch_name(self.environ, self.version)
        want = "testing-v0.0.0"
        self.assertEqual(got, want)


class TestCheckArtifact(unittest.TestCase):
    def test_success(self) -> None:
        version = "v1.1.1"
        want = True
        with tempfile.TemporaryDirectory() as test_folder_name:
            os.system(f"touch {test_folder_name}/test.py")
            os.system(f"touch {test_folder_name}/test-{version}.zip")
            got = check_artifacts(f"./test.py", test_folder_name, version)
        self.assertEqual(got, want)

    def test_no_artifact(self) -> None:
        version = "v1.1.1"
        with tempfile.TemporaryDirectory() as test_folder_name:
            with self.assertRaises(MissingArtifactException):
                check_artifacts("test-file.py", test_folder_name, version)

    def test_check_artifacts_no_zip(self) -> None:
        version = "v1.1.1"
        with tempfile.TemporaryDirectory() as test_folder_name:
            os.system(f"touch {test_folder_name}/test.py")
            with self.assertRaises(MissingArtifactException):
                check_artifacts(test_folder_name, test_folder_name, version)


class TestParseArguments(unittest.TestCase):
    def test_successfully_parsing_arguments(self) -> None:
        want = CliArguments(
            project="platsec-lambda-prowler-manager",
            version="v1.1.1",
            base="development",
        )
        input_args = [
            "--project",
            want.project,
            "--version",
            want.version,
            "--base",
            want.base,
        ]

        got = parse_arguments(input_args)

        self.assertEqual(got, want)

    def test_fail_invalid_base(self) -> None:
        config = CliArguments(
            project="platsec-lambda-prowler-manager", version="v1.1.1", base="burn"
        )
        input_args = [
            "--project",
            config.project,
            "--version",
            config.version,
            "--base",
            config.base,
        ]

        with self.assertRaises(SystemExit):
            parse_arguments(input_args)

    def test_fail_missing_argument(self) -> None:
        config = CliArguments(
            project="platsec-lambda-prowler-manager", version="v1.1.1", base="burn"
        )
        input_args = ["--project", config.project, "--version", config.version]

        with self.assertRaises(SystemExit):
            parse_arguments(input_args)

    def test_fail_invalid_version(self) -> None:
        config = CliArguments(
            project="platsec-lambda-prowler-manager", version="ggg.1.1", base="burn"
        )
        input_args = [
            "--project",
            config.project,
            "--version",
            config.version,
            "--base",
            config.base,
        ]

        with self.assertRaises(SystemExit):
            parse_arguments(input_args)


class TestUpdateRuntime(unittest.TestCase):
    maxDiff = None

    def test_if_default_exists(self) -> None:
        runtime = "3.8"
        variables_input = (
            f"./deployment_scripts/test/fixtures/{unittest.TestCase.id(self)}.input.tf"
        )
        want_content = get_content(
            f"./deployment_scripts/test/fixtures/{unittest.TestCase.id(self)}.want.tf"
        )

        with tempfile.TemporaryDirectory() as test_folder_name:
            variables_file = test_folder_name + "/variables.copy.tf"
            shutil.copyfile(variables_input, variables_file)
            update_runtime(runtime, variables_file)
            got_content = get_content(variables_file)

        self.assertEqual(got_content, want_content)

    def test_if_default_not_exists(self) -> None:
        runtime = "9.9"
        variables_input = (
            f"./deployment_scripts/test/fixtures/{unittest.TestCase.id(self)}.input.tf"
        )
        want_content = get_content(
            f"./deployment_scripts/test/fixtures/{unittest.TestCase.id(self)}.want.tf"
        )

        with tempfile.TemporaryDirectory() as test_folder_name:
            variables_file = test_folder_name + "/variables.copy.tf"
            shutil.copyfile(variables_input, variables_file)
            update_runtime(runtime, variables_file)
            got_content = get_content(variables_file)

        self.assertEqual(got_content, want_content)

    def test_variable_name_is_not_quoted(self) -> None:
        runtime = "3.9"
        variables_input = (
            f"./deployment_scripts/test/fixtures/{unittest.TestCase.id(self)}.input.tf"
        )
        want_content = get_content(
            f"./deployment_scripts/test/fixtures/{unittest.TestCase.id(self)}.want.tf"
        )

        with tempfile.TemporaryDirectory() as test_folder_name:
            variables_file = test_folder_name + "/variables.copy.tf"
            shutil.copyfile(variables_input, variables_file)
            update_runtime(runtime, variables_file)
            got_content = get_content(variables_file)

        self.assertEqual(got_content, want_content)


class TestUpdatePackageVersion(unittest.TestCase):
    def test_success_for_valid_input(self) -> None:
        version = "v1.1.1"
        variables_input = (
            f"./deployment_scripts/test/fixtures/{unittest.TestCase.id(self)}.input.tf"
        )
        want_content = get_content(
            f"./deployment_scripts/test/fixtures/{unittest.TestCase.id(self)}.want.tf"
        )

        with tempfile.TemporaryDirectory() as test_folder_name:
            variables_file = test_folder_name + "/variables.copy.tf"
            shutil.copyfile(variables_input, variables_file)
            update_package_version(version, variables_file)
            got_content = get_content(variables_file)

        self.assertEqual(got_content, want_content)

    def test_default_not_exist(self) -> None:
        version = "v1.1.1"
        variables_input = (
            f"./deployment_scripts/test/fixtures/{unittest.TestCase.id(self)}.input.tf"
        )
        want_content = get_content(
            f"./deployment_scripts/test/fixtures/{unittest.TestCase.id(self)}.want.tf"
        )

        with tempfile.TemporaryDirectory() as test_folder_name:
            variables_file = test_folder_name + "/variables.copy.tf"
            shutil.copyfile(variables_input, variables_file)
            update_package_version(version, variables_file)
            got_content = get_content(variables_file)

        self.assertEqual(got_content, want_content)

    def test_variable_name_is_not_quoted(self) -> None:
        version = "v1.1.1"
        variables_input = (
            f"./deployment_scripts/test/fixtures/{unittest.TestCase.id(self)}.input.tf"
        )
        want_content = get_content(
            f"./deployment_scripts/test/fixtures/{unittest.TestCase.id(self)}.want.tf"
        )

        with tempfile.TemporaryDirectory() as test_folder_name:
            variables_file = test_folder_name + "/variables.copy.tf"
            shutil.copyfile(variables_input, variables_file)
            update_package_version(version, variables_file)
            got_content = get_content(variables_file)

        self.assertEqual(got_content, want_content)


class TestGetPythonVersion(unittest.TestCase):
    def test_passing_valid_file_return_major_minor(self) -> None:
        input_file = "./deployment_scripts/test/fixtures/python-version-valid"
        want = "3.10"
        got = get_python_version(input_file)
        self.assertEqual(got, want)

    def test_passing_valid_file_with_major_only(self) -> None:
        input_file = "./deployment_scripts/test/fixtures/python-version-major-only"
        with self.assertRaises(InvalidSemverException):
            get_python_version(input_file)

    def test_pass_invalid_filepath(self) -> None:
        input_file = "./deployment_scripts/test/fixtures/nothing"
        with self.assertRaises(MissingFileException):
            get_python_version(input_file)

    def test_passing_file_with_invalid_version_format(self) -> None:
        input_file = "./deployment_scripts/test/fixtures/python-version-invalid"
        with self.assertRaises(InvalidSemverException):
            get_python_version(input_file)


def save_content(file: str, content: str) -> None:
    with open(file, "w") as f:
        f.write(content)


def get_content(file: str) -> str:
    with open(file, "r") as f:
        return f.read()


class TestGetenvOrRaise(unittest.TestCase):
    def setUpEnv(self) -> None:
        if self.token is None:
            return
        os.environ["TOKEN"] = self.token

    def test_get_correct_environment(self) -> None:
        """
        Validate environment variable TOKEN
        """
        self.token = "OTYwMDYwZGVlY2E2ZjRlMzJjYjYwYTllOTgwN"

        want_token = "OTYwMDYwZGVlY2E2ZjRlMzJjYjYwYTllOTgwN"

        self.setUpEnv()
        got_token = getenv_or_raise("TOKEN")

        self.assertEqual(got_token, want_token)

    def test_environment_with_whitepaces(self) -> None:
        """
        Use default value when env variable TOKEN is empty
        """
        self.token = "  \tOTYwMDYwZGVlY2E2ZjRlMzJjYjYwYTllOTgwN\n\r  "

        want_token = "OTYwMDYwZGVlY2E2ZjRlMzJjYjYwYTllOTgwN"

        self.setUpEnv()
        got_token = getenv_or_raise("TOKEN")

        self.assertEqual(got_token, want_token)

    def test_empty_environment(self) -> None:
        """
        Raise exception when env variable TOKEN is empty
        """
        self.token = ""

        self.setUpEnv()
        with self.assertRaises(GetEnvException):
            getenv_or_raise("TOKEN")

    def test_empty_environment_with_whitepaces(self) -> None:
        """
        Raise exception when env variable TOKEN is empty
        """
        self.token = "  \t\n\r  "

        self.setUpEnv()
        with self.assertRaises(GetEnvException):
            getenv_or_raise("TOKEN")

    def tearDown(self) -> None:
        os.environ.pop("TOKEN", None)


class TestGitClone(unittest.TestCase):
    def test_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            git = Git(
                user="user",
                token="token",
                repo_directory=directory,
                org="org",
                repository="repository",
            )
            want_args = [
                "git",
                "clone",
                f"https://{git.user}:{git.token}@github.com/{git.org}/{git.repository}.git",
                git.repo_directory,
            ]

            mock_run = Mock()
            mock_run.return_value = subprocess.CompletedProcess(
                args=want_args, returncode=0
            )

            try:
                with patch("subprocess.run", mock_run):
                    git.clone()

            except GitCloneException as err:
                self.fail(f"Exception should not be raised, but got:{err}")

        mock_run.assert_called_once_with(
            args=want_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )

    def test_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            git = Git(
                user="user",
                token="token",
                repo_directory=directory,
                org="org",
                repository="repository",
            )
            want_args = [
                "git",
                "clone",
                f"https://{git.user}:{git.token}@github.com/{git.org}/{git.repository}.git",
                git.repo_directory,
            ]

            mock_run = Mock()
            mock_run.return_value = subprocess.CompletedProcess(
                args=want_args,
                returncode=128,
                stdout=("fatal: some git error").encode("utf-8"),
            )

            with patch("subprocess.run", mock_run):
                with self.assertRaises(GitCloneException):
                    git.clone()

        mock_run.assert_called_once_with(
            args=want_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )


class TestGitPush(unittest.TestCase):
    def test_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            git = Git(
                user="user",
                token="token",
                repo_directory=directory,
                org="org",
                repository="repository",
            )
            branch = "branch"
            want_args = ["git", "push", "--set-upstream", "origin", branch]

            mock_run = Mock()
            mock_run.return_value = subprocess.CompletedProcess(
                args=want_args, returncode=0
            )

            try:
                with patch("subprocess.run", mock_run):
                    git.push(branch)

            except GitPushException as err:
                self.fail(f"Exception should not be raised, but got:{err}")

        mock_run.assert_called_once_with(
            args=want_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=git.repo_directory,
        )

    def test_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            git = Git(
                user="user",
                token="token",
                repo_directory=directory,
                org="org",
                repository="repository",
            )
            branch = "branch"
            want_args = ["git", "push", "--set-upstream", "origin", branch]

            mock_run = Mock()
            mock_run.return_value = subprocess.CompletedProcess(
                args=want_args,
                returncode=128,
                stdout=("fatal: some git error").encode("utf-8"),
            )

            with patch("subprocess.run", mock_run):
                with self.assertRaises(GitPushException):
                    git.push(branch)

        mock_run.assert_called_once_with(
            args=want_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=git.repo_directory,
        )


class TestGitCommit(unittest.TestCase):
    def test_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            git = Git(
                user="user",
                token="token",
                repo_directory=directory,
                org="org",
                repository="repository",
            )
            version = "v1.1.1"
            want_args = [
                "git",
                "commit",
                "-S",
                "-am",
                f"auto-generated commit for version {version}",
            ]

            mock_run = Mock()
            mock_run.return_value = subprocess.CompletedProcess(
                args=want_args, returncode=0
            )

            try:
                with patch("subprocess.run", mock_run):
                    git.commit(version)

            except GitCommitException as err:
                self.fail(f"Exception should not be raised, but got:{err}")

        mock_run.assert_called_once_with(
            args=want_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=git.repo_directory,
        )

    def test_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            git = Git(
                user="user",
                token="token",
                repo_directory=directory,
                org="org",
                repository="repository",
            )
            version = "v1.1.1"
            want_args = [
                "git",
                "commit",
                "-S",
                "-am",
                f"auto-generated commit for version {version}",
            ]

            mock_run = Mock()
            mock_run.return_value = subprocess.CompletedProcess(
                args=want_args,
                returncode=128,
                stdout=("fatal: some git error").encode("utf-8"),
            )

            with patch("subprocess.run", mock_run):
                with self.assertRaises(GitCommitException):
                    git.commit(version)

        mock_run.assert_called_once_with(
            args=want_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=git.repo_directory,
        )


class TestGitCheckout(unittest.TestCase):
    def test_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            git = Git(
                user="user",
                token="token",
                repo_directory=directory,
                org="org",
                repository="repository",
            )
            branch = "v1.1.1"
            want_args = ["git", "checkout", branch]

            mock_run = Mock()
            mock_run.return_value = subprocess.CompletedProcess(
                args=want_args, returncode=0
            )

            try:
                with patch("subprocess.run", mock_run):
                    git.checkout(branch)

            except GitCheckoutException as err:
                self.fail(f"Exception should not be raised, but got:{err}")

        mock_run.assert_called_once_with(
            args=want_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=git.repo_directory,
        )

    def test_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            git = Git(
                user="user",
                token="token",
                repo_directory=directory,
                org="org",
                repository="repository",
            )
            branch = "v1.1.1"
            want_args = ["git", "checkout", branch]

            mock_run = Mock()
            mock_run.return_value = subprocess.CompletedProcess(
                args=want_args,
                returncode=128,
                stdout=("fatal: some git error").encode("utf-8"),
            )

            with patch("subprocess.run", mock_run):
                with self.assertRaises(GitCheckoutException):
                    git.checkout(branch)

        mock_run.assert_called_once_with(
            args=want_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=git.repo_directory,
        )


class TestGitBranch(unittest.TestCase):
    def test_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            git = Git(
                user="user",
                token="token",
                repo_directory=directory,
                org="org",
                repository="repository",
            )
            name = "v1.1.1"
            base = "main"
            want_args = ["git", "branch", name, base]

            mock_run = Mock()
            mock_run.return_value = subprocess.CompletedProcess(
                args=want_args, returncode=0
            )

            try:
                with patch("subprocess.run", mock_run):
                    git.branch(name, base)

            except GitBranchException as err:
                self.fail(f"Exception should not be raised, but got:{err}")

        mock_run.assert_called_once_with(
            args=want_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=git.repo_directory,
        )

    def test_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            git = Git(
                user="user",
                token="token",
                repo_directory=directory,
                org="org",
                repository="repository",
            )
            name = "v1.1.1"
            base = "main"
            want_args = ["git", "branch", name, base]

            mock_run = Mock()
            mock_run.return_value = subprocess.CompletedProcess(
                args=want_args,
                returncode=128,
                stdout=("fatal: some git error").encode("utf-8"),
            )

            with patch("subprocess.run", mock_run):
                with self.assertRaises(GitBranchException):
                    git.branch(name, base)

        mock_run.assert_called_once_with(
            args=want_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=git.repo_directory,
        )


class TestAreFilesChanged(unittest.TestCase):
    def test_success_files_changed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            git = Git(
                user="user",
                token="token",
                repo_directory=directory,
                org="org",
                repository="repository",
            )
            want_args = ["git", "diff", "--quiet", "HEAD"]
            want_diff_return_code = 1
            want_return = True

            mock_run = Mock()
            mock_run.return_value = subprocess.CompletedProcess(
                args=want_args, returncode=want_diff_return_code
            )

            try:
                with patch("subprocess.run", mock_run):
                    got_return = git.are_files_changed()

            except GitDiffException as err:
                self.fail(f"Exception should not be raised, but got:{err}")

        mock_run.assert_called_once_with(
            args=want_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=git.repo_directory,
        )
        self.assertEqual(got_return, want_return)

    def test_success_files_not_changed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            git = Git(
                user="user",
                token="token",
                repo_directory=directory,
                org="org",
                repository="repository",
            )
            want_args = ["git", "diff", "--quiet", "HEAD"]
            want_diff_return_code = 0
            want_return = False

            mock_run = Mock()
            mock_run.return_value = subprocess.CompletedProcess(
                args=want_args, returncode=want_diff_return_code
            )

            try:
                with patch("subprocess.run", mock_run):
                    got_return = git.are_files_changed()

            except GitDiffException as err:
                self.fail(f"Exception should not be raised, but got:{err}")

        mock_run.assert_called_once_with(
            args=want_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=git.repo_directory,
        )
        self.assertEqual(got_return, want_return)

    def test_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            git = Git(
                user="user",
                token="token",
                repo_directory=directory,
                org="org",
                repository="repository",
            )
            want_args = ["git", "diff", "--quiet", "HEAD"]

            mock_run = Mock()
            mock_run.return_value = subprocess.CompletedProcess(
                args=want_args,
                returncode=129,
                stdout=("fatal: some git error").encode("utf-8"),
            )

            with patch("subprocess.run", mock_run):
                with self.assertRaises(GitDiffException):
                    git.are_files_changed()

        mock_run.assert_called_once_with(
            args=want_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=git.repo_directory,
        )


class TestGitHubHeaders(unittest.TestCase):
    git = Git(
        user="user",
        token="token",
        repo_directory="not_relevant",
        org="org",
        repository="repository",
    )

    def test_required_headers(self) -> None:
        git = Git(
            user="user",
            token="token",
            repo_directory="not_relevant",
            org="org",
            repository="repository",
        )
        want = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {git.token}",
            "Content-Type": "application/json",
        }

        got = git.headers()
        self.assertEqual(got, want)


class TestPullRequestExists(unittest.TestCase):
    git = Git(
        user="user",
        token="token",
        repo_directory="not_relevant",
        org="org",
        repository="repository",
    )

    @httpretty.activate
    def test_success_pr_exists(self) -> None:
        base = "main"
        branch = "feature"
        url = f"{self.git.api_pr_url()}?base={base}&head={branch}"
        httpretty.register_uri(
            httpretty.GET,
            url,
            status=200,
            body=json.dumps(
                [{"url": "https://first.url"}, {"url": "https://second.url"}]
            ),
        )
        got = self.git.pull_request_exists(branch, base)
        want = True
        self.assertEqual(got, want)

    @httpretty.activate
    def test_success_pr_does_not_exist(self) -> None:
        base = "main"
        branch = "feature"
        url = f"{self.git.api_pr_url()}?base={base}&head={branch}"
        httpretty.register_uri(
            httpretty.GET,
            url,
            status=200,
            body=json.dumps([]),
        )
        got = self.git.pull_request_exists(branch, base)
        want = False
        self.assertEqual(got, want)

    @httpretty.activate
    def test_fail_from_github(self) -> None:
        base = "main"
        branch = "feature"
        url = f"{self.git.api_pr_url()}?base={base}&head={branch}"
        httpretty.register_uri(
            httpretty.GET,
            url,
            status=500,
        )
        with self.assertRaises(GitPullRequestException):
            self.git.pull_request_exists(branch, base)


class TestPullRequest(unittest.TestCase):
    git = Git(
        user="user",
        token="token",
        repo_directory="not_relevant",
        org="org",
        repository="repository",
    )

    @httpretty.activate
    def test_success(self) -> None:
        base = "main"
        branch = "feature"
        want_url = "https://first.url"
        url = f"{self.git.api_pr_url()}?base={base}&head={branch}"
        httpretty.register_uri(
            httpretty.POST,
            url,
            status=201,
            body=json.dumps({"html_url": want_url}),
        )
        got_url = self.git.pull_request(branch, base)
        self.assertEqual(got_url, want_url)

    @httpretty.activate
    def test_fail_from_github(self) -> None:
        base = "main"
        branch = "feature"
        url = f"{self.git.api_pr_url()}"
        httpretty.register_uri(
            httpretty.POST,
            url,
            status=500,
        )
        with self.assertRaises(GitPullRequestException):
            self.git.pull_request(branch, base)
