variable "guardduty_monitoring_lambda_runtime" {
  description = "Lambda runtime of GuardDuty function"
  default     = "python3.8"
}

variable "prowler_scanner_lambda_runtime" {
  description = "Lambda runtime of Prowler function"
  default     = "python9.9"
}
