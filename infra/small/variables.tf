variable "project" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,23}$", var.project))
    error_message = "Project must be a safe lowercase slug, 3-24 characters."
  }
}
variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "staging"], var.environment)
    error_message = "The SSM lab is for dev/staging only."
  }
}
variable "region" {
  type = string
}
variable "size" {
  type = string
  validation {
    condition     = var.size == "small"
    error_message = "Only small is implemented in this root module."
  }
}
variable "instance_type" {
  type = string
  validation {
    condition     = contains(["t3.small", "t3.medium", "t3.large"], var.instance_type)
    error_message = "Use a supported x86_64 T3 instance."
  }
}
variable "volume_gib" {
  type = number
  validation {
    condition     = var.volume_gib >= 20 && var.volume_gib <= 200 && floor(var.volume_gib) == var.volume_gib
    error_message = "Volume must be an integer from 20 to 200 GiB."
  }
}
variable "moodle_version" {
  type = string
  validation {
    condition     = var.moodle_version == "4.5.15"
    error_message = "This bootstrap supports the pinned release 4.5.15."
  }
}
variable "wwwroot" {
  type = string
  validation {
    condition     = var.wwwroot == "http://localhost:8080"
    error_message = "Use the SSM local endpoint http://localhost:8080."
  }
}
variable "backup_bucket" {
  type    = string
  default = ""
  validation {
    condition     = var.backup_bucket == "" || can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.backup_bucket))
    error_message = "Use an existing S3 bucket name, without s3:// or a path."
  }
}
variable "tags" {
  type    = map(string)
  default = {}
}
variable "additional_security_group_ids" {
  type    = list(string)
  default = []
  validation {
    condition     = alltrue([for id in var.additional_security_group_ids : can(regex("^sg-[a-f0-9]+$", id))])
    error_message = "Additional security groups must be EC2 group IDs."
  }
}
variable "public_url" {
  type    = string
  default = ""
  validation {
    condition     = var.public_url == "" || can(regex("^https://[a-z0-9]+\\.cloudfront\\.net$", var.public_url))
    error_message = "The optional public endpoint must be a CloudFront HTTPS URL."
  }
}
