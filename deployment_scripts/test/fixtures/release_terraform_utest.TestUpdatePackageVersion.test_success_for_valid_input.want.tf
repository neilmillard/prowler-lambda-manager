variable "github_scanner_lambda_artifact_key" {
  description = "Artifact version of the Github scanner tool"
  default     = "github-scanner-lambda-1.1.4.zip"
}

variable "prowler_runner_lambda_artifact_key" {
  description = "Artifact version Of Prowler runner"
  default     = "platsec-lambda-prowler-manager-v1.1.1.zip"
}
