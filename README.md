
# PlatSec Prowler Checks

[AWS](https://aws.amazon.com/) accounts on the Platform need to be benchmarked for security compliance on a scheduled basis.
Infrastructure that is not compliant needs to be reported to the Teams that own the accounts for remediation.
[Prowler](https://github.com/toniblyx/prowler) is an open source tool that tests an AWS account against a set of security and compliance checks that have been written in Bash.

The checks are then grouped together in pre-defined groups.  Currently, there are twenty one groups covering common standards such as:

* [HIPAA](https://www.cdc.gov/phlp/publications/topic/hipaa.html)
* [SOC](https://www.itgovernance.co.uk/soc-reporting)
* [CIS](https://www.cisecurity.org)

as well as more specific technology area groupings around:

* networking,
* RDS (Relational Database Service)
* [SageMaker](https://aws.amazon.com/sagemaker/)

This solution will deliver the capability of scheduled checks against MDTP’s AWS infrastructure highlighting issues, concerns and best practices against well defined benchmarks.

This project allows for teams to create their own custom checks.  A check is essentially a Bash script that executes API calls against the AWS cloud platform.

PlatSec has created a group that is a cut down of CIS level 2 checks and this is to be considered as the baseline security stance that will be run against all accounts.

The baseline checks are called group20_Platsec. These will always be run against *all* accounts in the organization. Tests set by the teams will be run in addition to the baseline checks. If teams have not set their own checks, the baseline checks will still be run.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

You will need the following installed on your machine:

* GNU Make
* Python version >= 3.8.x
* [Pipenv](https://pypi.org/project/pipenv/)

### Installing

All dependencies are defined in the [Pipfile](./Pipfile)
In the root of the project, run `pipenv install`

## Running the tests

Tests are run from the project root.
Before running tests, you will need to setup the environment. To do this, run `make setup`

* To run all tests, run `make test`
* To run only unit tests, run `make python-unit-test`
* To run only integrations tests, run `make python-integration-test`
* To run coverage check, run `make python-coverage-only`

## Architecture

PlatSec has adopted a serverless architecture for running the prowler checks. Instead of provisioning EC2 instances, which may take a while to become ready, or be running 24/7/365 when only needed for 15 mins a day/week, the system utilises the following AWS services:

* S3
* lambda
* Cloudwatch
* SQS
* SNS

An architectural diagram can be seen [here](https://docs.google.com/document/d/1t8khI9Jyf2d6vSihrIXLNRYKggiVeGNzQPowheTv6nk/edit#heading=h.7jd1ryw3xurc)

## Deployment

Deployment is via a [AWS Codebuild](https://aws.amazon.com/codebuild/) job, whose phases and steps are declared in the [buildspec.yml](buildspec.yml) file. These steps are:

1. **make setup** sets up the environment
2. **make test** - runs the test scripts.
3. **./setup_gpg.sh** - runs the script which prepares GPG key and git commit signing.
4. **make package** - uses bash to create lambda deployment package.
5. **make publish-&lt;environment&gt;** - runs *make generate-sha256* which creates hashed versions of the zip archives. Then it copies the zip archives and the hashed versions, to the relevant S3 bucket.
6. **make pr-for-&lt;environment&gt;** runs the [terraform pr builder](#pr_builder) python script.

&lt;environment&gt; is either *production*, *development*  or *sandbox*

### Deployment scripts

<a name="pr_builder"></a>deployment_scripts/release_terraform_pr.py
This script has several functions. It performs the following tasks:

1. Clone platsec terraform repo.
2. Check out a new branch in the repo.
3. In terraform variables file for the environment:
    * update python_runtime variable.
    * replace artifact version numbers with those of the latest tag.
4. Commits & pushes the changes.
5. Creates a new PR in the platsec terraform repo.

### Tagging

After pushing to Git and merging into main branch, you will need to increment the version,
by creating a git tag:

1. Check latest tag. Run `git tag`
2. Create new tag. Run `git tag vN.N.N`
3. Run `git push vN.N.N`

N.N.N is the version number and must follow the [SemVer](https://semver.org) format

### Terraform

Pushing a new tag will result in a new pull request being created in the platsec-terraform branch, with the tag of the new code being inserted into the relevant terraform template file. The runtime will also be replaced where appropriate.

## Development

### Codebuild

In order to reduce the feedback time during development, AWS Codebuild can be ran locally using [Docker images provided by AWS](https://github.com/aws/aws-codebuild-docker-images). Please see [this guide](https://www.shogan.co.uk/devops/aws-codebuild-local-with-docker/).

If you intend to use AWS Codebuild locally, you will need to create a local `.env` file:

1. run `cp env_sample .env`
2. Open your new .env file and polpulate the following with dummy values:
    * ENVIRONMENT=sandbox
    * GITHUB_API_TOKEN=
    * GITHUB_API_USER=
    * GITHUB_API_EMAIL=
3. [Create a GPG key](https://docs.github.com/en/github/authenticating-to-github/generating-a-new-gpg-key) - this key is for develoment/testing only.
4. Base64 encode your new key
5. Split your key into three parts and populate the following variables with each of the three parts:
    * GPG_PRIVATE_KEY_1
    * GPG_PRIVATE_KEY_2
    * GPG_PRIVATE_KEY_3

### Code for Lambda

There are two python scripts, which will be deployed to [AWS Lambda](https://aws.amazon.com/lambda/).
They can be found in *src/handlers/*

**Platsec Prowler Lambda Manager Script**
This is the orchestrator. It obtains lists of all accounts in the [AWS Organization](https://aws.amazon.com/organizations/), along with the groups of checks to by run on the specific account. It then sends these, individually, to [SQS](https://aws.amazon.com/sqs/)
The payload for each, will look liks this:

```json
{
    "Id": "<AWS_ACCOUNT_NUMBER>",
    "Name": "<AWS_ACCOUNT_NAME>",
    "Groups": [
        n,
        n,
        n
    ]
}
```

Account payloads are send individually to SQS, so that there is one invokation per account - reduces the possibility of lambda timeout as we will have almost simultaneous invokations for each account.

### Prowler Library Files

The prowler library files are contained in a Docker image, which resides in [AWS ECR](https://aws.amazon.com/ecr/). These are deployed separately to AWS Lambda, by Terraform

## Built With

* [Prowler](https://github.com/toniblyx/prowler) - Security tool
