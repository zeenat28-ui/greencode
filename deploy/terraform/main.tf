# GreenCode Enterprise Multi-Cloud Infrastructure as Code (Terraform)
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
  }

  backend "s3" {
    bucket         = "greencode-terraform-state-prod"
    key            = "enterprise/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "greencode-terraform-locks"
  }
}

variable "environment" {
  type        = string
  default     = "production"
  description = "Target environment (staging, production)"
}

variable "cloud_provider" {
  type        = string
  default     = "aws"
  description = "Primary enterprise cloud provider (aws, azure, gcp)"
}

variable "db_instance_class" {
  type        = string
  default     = "db.r6g.xlarge" # High efficiency AWS Graviton
  description = "Database compute tier"
}

