terraform {
  required_version = ">= 1.10, < 2"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  backend "local" {}
}
variable "region" { type = string }
variable "account_id" { type = string }
variable "name" { type = string }
variable "vpc_id" { type = string }
variable "network_interface_id" { type = string }
variable "origin_dns" { type = string }
variable "instance_role" { type = string }
variable "origin_token" {
  type      = string
  sensitive = true
  validation {
    condition     = can(regex("^[a-f0-9]{64}$", var.origin_token))
    error_message = "Use a generated 256-bit origin token."
  }
}
provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
  default_tags { tags = { Project = var.name, ManagedBy = "Terraform", Purpose = "small-public" } }
}
data "aws_ec2_managed_prefix_list" "cloudfront" { name = "com.amazonaws.global.cloudfront.origin-facing" }
data "aws_cloudfront_cache_policy" "disabled" { name = "Managed-CachingDisabled" }
data "aws_cloudfront_origin_request_policy" "viewer" { name = "Managed-AllViewer" }
data "aws_cloudfront_response_headers_policy" "security" { name = "Managed-SecurityHeadersPolicy" }
resource "aws_security_group" "origin" {
  name_prefix = "${var.name}-public-"
  description = "CloudFront origin only; application also requires a private origin header"
  vpc_id      = var.vpc_id
}
resource "aws_vpc_security_group_ingress_rule" "edge" {
  security_group_id = aws_security_group.origin.id
  prefix_list_id    = data.aws_ec2_managed_prefix_list.cloudfront.id
  from_port         = 8081
  to_port           = 8081
  ip_protocol       = "tcp"
}
resource "aws_network_interface_sg_attachment" "origin" {
  security_group_id    = aws_security_group.origin.id
  network_interface_id = var.network_interface_id
}
resource "aws_secretsmanager_secret" "origin" {
  name_prefix             = "${var.name}-public-origin-"
  recovery_window_in_days = 7
}
resource "aws_secretsmanager_secret_version" "origin" {
  secret_id     = aws_secretsmanager_secret.origin.id
  secret_string = var.origin_token
}
resource "aws_iam_role_policy" "origin" {
  name_prefix = "small-public-origin-"
  role        = var.instance_role
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = aws_secretsmanager_secret.origin.arn
  }] })
}
resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  comment             = "${var.name} small Moodle HTTPS"
  is_ipv6_enabled     = true
  wait_for_deployment = true
  price_class         = "PriceClass_All"
  origin {
    domain_name = var.origin_dns
    origin_id   = "small-ec2"
    custom_header {
      name  = "X-Moodle-Origin"
      value = var.origin_token
    }
    custom_origin_config {
      http_port              = 8081
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
      origin_read_timeout    = 60
    }
  }
  default_cache_behavior {
    target_origin_id           = "small-ec2"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.viewer.id
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.security.id
  }
  viewer_certificate { cloudfront_default_certificate = true }
  restrictions {
    geo_restriction { restriction_type = "none" }
  }
  dynamic "custom_error_response" {
    for_each = toset([500, 502, 503, 504])
    content {
      error_code            = custom_error_response.value
      error_caching_min_ttl = 0
    }
  }
}
output "url" { value = "https://${aws_cloudfront_distribution.site.domain_name}" }
output "distribution_id" { value = aws_cloudfront_distribution.site.id }
output "origin_secret_arn" { value = aws_secretsmanager_secret.origin.arn }
