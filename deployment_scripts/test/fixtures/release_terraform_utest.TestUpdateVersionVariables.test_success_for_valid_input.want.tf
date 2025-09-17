variable "guardduty_monitoring_lambda_runtime" {
  description = "Lambda runtime of GuardDuty function"
  default     = "python3.8"
}

variable "prowler_scanner_lambda_runtime" {
  description = "Lambda runtime of Prowler function"
  default     = "python3.8"
}

variable "github_scanner_lambda_artifact_key" {
  description = "Artifact version of the Github scanner tool"
  default     = "github-scanner-lambda-1.1.4.zip"
}

variable "prowler_runner_lambda_artifact_key" {
  description = "Artifact version Of Prowler runner"
  default     = "platsec-lambda-prowler-manager-v0.1.0.zip"
}
