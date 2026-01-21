variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "complaint-platform"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "complaint-platform-cluster"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "enable_monitoring" {
  description = "Enable enhanced monitoring and logging"
  type        = bool
  default     = true
}

variable "enable_backup" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}
