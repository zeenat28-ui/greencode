# AWS High-Availability & Low-Carbon Infrastructure for GreenCode
provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = {
      Project     = "GreenCode-Auditor"
      Environment = var.environment
      ManagedBy   = "Terraform"
      SustainabilityTier = "Carbon-Optimized-ARM64"
    }
  }
}

# Amazon RDS PostgreSQL Multi-AZ Cluster (Graviton ARM64)
resource "aws_db_instance" "greencode_postgres" {
  identifier            = "greencode-${var.environment}-pg"
  engine                = "postgres"
  engine_version        = "15.4"
  instance_class        = var.db_instance_class
  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_type          = "gp3"
  multi_az              = true
  publicly_accessible   = false
  db_name               = "greencode"
  username              = "greencode_admin"
  password              = "ReplaceWithKmsSecretEnterprise2026!"
  skip_final_snapshot   = false
  deletion_protection   = true

  performance_insights_enabled = true
  backup_retention_period      = 30
}

# Amazon ElastiCache Redis Cluster for Distributed Rate Limiting & Token Revocation
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id          = "greencode-${var.environment}-redis"
  replication_group_description = "GreenCode Token Revocation and Cache Cluster"
  node_type                     = "cache.t4g.medium" # ARM64 energy efficient
  num_cache_clusters            = 2
  automatic_failover_enabled    = true
  at_rest_encryption_enabled    = true
  transit_encryption_enabled    = true
  port                          = 6379
}

# Application Load Balancer
resource "aws_lb" "alb" {
  name               = "greencode-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = ["subnet-12345678", "subnet-87654321"]
  enable_deletion_protection = true
}

