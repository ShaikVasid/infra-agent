variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Application name — used to name all resources"
  type        = string
  default     = "infrabot"
}

variable "google_api_key" {
  description = "Google Gemini API key"
  type        = string
  sensitive   = true
}

variable "aws_access_key_id" {
  description = "AWS Access Key ID for InfraBot to call AWS APIs"
  type        = string
  sensitive   = true
}

variable "aws_secret_access_key" {
  description = "AWS Secret Access Key for InfraBot to call AWS APIs"
  type        = string
  sensitive   = true
}

variable "container_port" {
  description = "Port Streamlit listens on"
  type        = number
  default     = 8501
}

variable "cpu" {
  description = "Fargate task CPU units (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Fargate task memory in MB"
  type        = number
  default     = 512
}
