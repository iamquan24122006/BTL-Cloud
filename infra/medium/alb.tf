resource "aws_lb" "medium" {
  name                       = substr(local.name, 0, 32)
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = [for s in aws_subnet.public : s.id]
  drop_invalid_header_fields = true
  preserve_host_header       = true
  idle_timeout               = 120
}
resource "aws_lb_target_group" "app" {
  name_prefix          = "mdl-"
  port                 = 8080
  protocol             = "HTTP"
  vpc_id               = aws_vpc.medium.id
  deregistration_delay = 120
  health_check {
    path                = "/_ready.php"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
  stickiness {
    type    = "lb_cookie"
    enabled = false
  }
}
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.medium.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = var.frontend == "acm" ? "redirect" : "forward"
    target_group_arn = var.frontend == "cloudfront" ? aws_lb_target_group.app.arn : null
    dynamic "redirect" {
      for_each = var.frontend == "acm" ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }
}
resource "aws_lb_listener" "https" {
  count             = var.frontend == "acm" ? 1 : 0
  load_balancer_arn = aws_lb.medium.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.certificate_arn
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
resource "aws_route53_record" "medium" {
  count   = var.frontend == "acm" && var.hosted_zone_id != "" ? 1 : 0
  zone_id = var.hosted_zone_id
  name    = var.domain
  type    = "A"
  alias {
    name                   = aws_lb.medium.dns_name
    zone_id                = aws_lb.medium.zone_id
    evaluate_target_health = true
  }
}
