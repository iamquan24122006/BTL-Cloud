terraform {
  required_version = ">= 1.10.0, < 2.0.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  backend "local" {}
}
variable "region" { type = string }
variable "account_id" { type = string }
variable "project" { type = string }
variable "environment" { type = string }
provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
  default_tags {
    tags = { Project = var.project, Environment = var.environment, Owner = "N2", Purpose = "coursework" }
  }
}
locals { name = "${var.project}-${var.environment}" }
resource "aws_s3_bucket" "lab" {
  for_each      = toset(["state", "artifacts", "backups"])
  bucket        = "${local.name}-${var.account_id}-${var.region}-${each.key}"
  force_destroy = false
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket_versioning" "lab" {
  for_each = aws_s3_bucket.lab
  bucket   = each.value.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "lab" {
  for_each = aws_s3_bucket.lab
  bucket   = each.value.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_public_access_block" "lab" {
  for_each                = aws_s3_bucket.lab
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_policy" "lab" {
  for_each = aws_s3_bucket.lab
  bucket   = each.value.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Deny", Principal = "*", Action = "s3:*", Resource = [each.value.arn, "${each.value.arn}/*"], Condition = { Bool = { "aws:SecureTransport" = "false" } } }]
  })
}
resource "aws_ecr_repository" "moodle" {
  name                 = "${local.name}/moodle"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
}
# Only metadata is managed here. Values are generated in memory and uploaded via
# the AWS SDK/CLI, never passed as Terraform inputs or written into source YAML.
resource "aws_secretsmanager_secret" "lab" {
  for_each                = toset(["runtime", "migration", "redis"])
  name                    = "${local.name}/${each.key}"
  recovery_window_in_days = 7
}
output "buckets" { value = { for key, value in aws_s3_bucket.lab : key => value.id } }
output "repository_uri" { value = aws_ecr_repository.moodle.repository_url }
output "secret_arns" { value = { for key, value in aws_secretsmanager_secret.lab : key => value.arn } }
