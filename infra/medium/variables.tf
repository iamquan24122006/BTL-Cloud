variable "project" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,23}$", var.project))
    error_message = "Use a safe lowercase project slug."
  }
}
variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "staging"], var.environment)
    error_message = "Only dev/staging labs are supported."
  }
}
variable "size" {
  type = string
  validation {
    condition     = var.size == "medium"
    error_message = "This root supports medium only."
  }
}
variable "region" { type = string }
variable "account_id" { type = string }
variable "instance_type" { type = string }
variable "volume_gib" { type = number }
variable "moodle_version" {
  type = string
  validation {
    condition     = var.moodle_version == "4.5.15"
    error_message = "Keep the Moodle baseline pinned to 4.5.15."
  }
}
variable "wwwroot" {
  type = string
  validation {
    condition     = var.frontend == "cloudfront" ? var.wwwroot == "auto" : var.wwwroot == "https://${var.domain}"
    error_message = "wwwroot must be https://domain for ACM, or auto for the temporary CloudFront lab."
  }
}
variable "domain" { type = string }
variable "frontend" {
  type    = string
  default = "acm"
  validation {
    condition     = contains(["acm", "cloudfront"], var.frontend)
    error_message = "Choose acm or the explicitly limited cloudfront lab mode."
  }
}
variable "certificate_arn" { type = string }
variable "retain_cloudfront" {
  type    = bool
  default = false
  validation {
    condition     = !var.retain_cloudfront || var.frontend == "acm"
    error_message = "retain_cloudfront is only for preserving a previous CloudFront URL when switching to ACM."
  }
}
variable "hosted_zone_id" { type = string }
variable "ami_id" { type = string }
variable "availability_zones" {
  type = list(string)
  validation {
    condition     = length(var.availability_zones) == 2 && length(distinct(var.availability_zones)) == 2
    error_message = "Exactly two distinct availability zones are required."
  }
}
variable "vpc_cidr" { type = string }
variable "db_instance_type" { type = string }
variable "db_allocated_storage" { type = number }
variable "db_backup_retention_days" {
  type    = number
  default = 7
  validation {
    condition     = var.db_backup_retention_days >= 1 && var.db_backup_retention_days <= 35 && floor(var.db_backup_retention_days) == var.db_backup_retention_days
    error_message = "Keep automated backups enabled with an integer retention from 1 to 35 days."
  }
}
variable "redis_node_type" { type = string }
variable "app_requests_per_target" {
  type    = number
  default = 600
  validation {
    condition     = var.app_requests_per_target >= 60 && var.app_requests_per_target <= 6000 && floor(var.app_requests_per_target) == var.app_requests_per_target
    error_message = "Use an integer from 60 to 6000 requests per target per minute."
  }
}
variable "backup_bucket" { type = string }
variable "restore_source_prefix" {
  type    = string
  default = ""
}
variable "tags" { type = map(string) }
variable "artifact" {
  type = object({ image = string, release = string, bucket = string, key = string, sha256 = string })
  validation {
    condition     = can(regex("@sha256:[a-f0-9]{64}$", var.artifact.image)) && can(regex("^[a-f0-9]{64}$", var.artifact.sha256)) && can(regex("^[a-f0-9]{40}$", var.artifact.release))
    error_message = "Use an immutable ECR digest, source commit and verified bundle checksum."
  }
}
variable "secrets" {
  type = object({ runtime_arn = string, migration_arn = string, redis_arn = string, redis_version = string, admin_arn = optional(string, "") })
}
