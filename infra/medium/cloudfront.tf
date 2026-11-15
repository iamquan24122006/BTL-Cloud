# Temporary lab access explicitly chosen when no owned domain is available.
# It does NOT satisfy MED-02's separate requirement for HTTPS at ALB.
locals {
  cloudfront_enabled = var.frontend == "cloudfront" || var.retain_cloudfront
  public_url         = var.frontend == "cloudfront" ? "https://${aws_cloudfront_distribution.lab[0].domain_name}" : var.wwwroot
}
data "aws_ec2_managed_prefix_list" "cloudfront" {
  count = local.cloudfront_enabled ? 1 : 0
  name  = "com.amazonaws.global.cloudfront.origin-facing"
}
resource "aws_vpc_security_group_ingress_rule" "cloudfront" {
  count             = local.cloudfront_enabled ? 1 : 0
  security_group_id = aws_security_group.alb.id
  prefix_list_id    = data.aws_ec2_managed_prefix_list.cloudfront[0].id
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}
data "aws_cloudfront_cache_policy" "disabled" {
  count = local.cloudfront_enabled ? 1 : 0
  name  = "Managed-CachingDisabled"
}
data "aws_cloudfront_origin_request_policy" "viewer" {
  count = local.cloudfront_enabled ? 1 : 0
  name  = "Managed-AllViewer"
}
resource "aws_cloudfront_distribution" "lab" {
  count               = local.cloudfront_enabled ? 1 : 0
  enabled             = true
  comment             = "${local.name} temporary HTTPS lab; MED-02 remains pending"
  is_ipv6_enabled     = true
  price_class         = "PriceClass_All"
  wait_for_deployment = true
  origin {
    domain_name = aws_lb.medium.dns_name
    origin_id   = "moodle-alb"
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
      origin_read_timeout    = 60
    }
  }
  default_cache_behavior {
    target_origin_id         = "moodle-alb"
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD"]
    viewer_protocol_policy   = "redirect-to-https"
    compress                 = true
    cache_policy_id          = data.aws_cloudfront_cache_policy.disabled[0].id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.viewer[0].id
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
