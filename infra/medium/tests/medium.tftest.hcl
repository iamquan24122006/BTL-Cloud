mock_provider "aws" {
  mock_resource "aws_iam_service_linked_role" {
    defaults = { arn = "arn:aws:iam::111111111111:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling_moodle-test" }
  }
  mock_data "aws_ec2_managed_prefix_list" {
    defaults = { id = "pl-00000000000000000" }
  }
  mock_data "aws_cloudfront_cache_policy" {
    defaults = { id = "413f1609-65b9-4d8f-a3be-28beefd8e47b" }
  }
  mock_data "aws_cloudfront_origin_request_policy" {
    defaults = { id = "216adef6-5c7f-47e4-b989-5492eafa07d3" }
  }
  mock_resource "aws_cloudfront_distribution" {
    defaults = { domain_name = "test.cloudfront.net" }
  }
  mock_resource "aws_launch_template" {
    defaults = { id = "lt-00000000000000000" }
  }
  mock_resource "aws_lb" {
    defaults = { arn = "arn:aws:elasticloadbalancing:ap-southeast-1:111111111111:loadbalancer/app/moodle/0000000000000000" }
  }
  mock_resource "aws_lb_target_group" {
    defaults = { arn = "arn:aws:elasticloadbalancing:ap-southeast-1:111111111111:targetgroup/moodle/0000000000000000" }
  }
  mock_data "aws_secretsmanager_secret_version" {
    defaults = { secret_string = "{\"token\":\"TestingToken1234567890\"}" }
  }
  mock_resource "aws_db_instance" {
    defaults = {
      address            = "moodle.example.ap-southeast-1.rds.amazonaws.com"
      master_user_secret = [{ secret_arn = "arn:aws:secretsmanager:ap-southeast-1:111111111111:secret:master-abcdef", secret_status = "active", kms_key_id = "test" }]
    }
  }
}
run "temporary_https_without_private_response_cache" {
  command = apply
  variables {
    frontend        = "cloudfront"
    domain          = ""
    certificate_arn = ""
    wwwroot         = "auto"
  }
  assert {
    condition     = length(aws_vpc_security_group_ingress_rule.public) == 0 && length(aws_vpc_security_group_ingress_rule.cloudfront) == 1
    error_message = "Temporary HTTP origin must only accept CloudFront origin traffic."
  }
  assert {
    condition     = local.public_url == "https://test.cloudfront.net" && length(aws_lb_listener.https) == 0
    error_message = "CloudFront lab exposes a temporary HTTPS URL and does not claim HTTPS at ALB."
  }
  assert {
    condition     = aws_cloudfront_distribution.lab[0].default_cache_behavior[0].cache_policy_id == data.aws_cloudfront_cache_policy.disabled[0].id
    error_message = "Private Moodle responses must never be cached by CloudFront."
  }
}
variables {
  project              = "moodle-test"
  environment          = "dev"
  region               = "ap-southeast-1"
  size                 = "medium"
  account_id           = "111111111111"
  instance_type        = "t3.medium"
  volume_gib           = 30
  moodle_version       = "4.5.15"
  domain               = "moodle.example.com"
  wwwroot              = "https://moodle.example.com"
  certificate_arn      = "arn:aws:acm:ap-southeast-1:111111111111:certificate/00000000-0000-0000-0000-000000000000"
  hosted_zone_id       = ""
  ami_id               = "ami-00000000000000000"
  availability_zones   = ["ap-southeast-1a", "ap-southeast-1b"]
  vpc_cidr             = "10.43.0.0/16"
  db_instance_type     = "db.t4g.micro"
  db_allocated_storage = 20
  redis_node_type      = "cache.t4g.micro"
  backup_bucket        = "moodle-test-backup"
  tags                 = {}
  artifact = {
    image   = "111111111111.dkr.ecr.ap-southeast-1.amazonaws.com/moodle@sha256:0000000000000000000000000000000000000000000000000000000000000000"
    release = "0000000000000000000000000000000000000000"
    bucket  = "moodle-test-artifact"
    key     = "releases/test.tar.gz"
    sha256  = "0000000000000000000000000000000000000000000000000000000000000000"
  }
  secrets = {
    runtime_arn   = "arn:aws:secretsmanager:ap-southeast-1:111111111111:secret:runtime-abcdef"
    migration_arn = "arn:aws:secretsmanager:ap-southeast-1:111111111111:secret:migration-abcdef"
    redis_arn     = "arn:aws:secretsmanager:ap-southeast-1:111111111111:secret:redis-abcdef"
    redis_version = "00000000-0000-0000-0000-000000000000"
  }
}
run "bounded_private_cluster" {
  command = apply # All resources/data are mocked; no AWS API calls.
  assert {
    condition     = aws_autoscaling_group.app.min_size == 2 && aws_autoscaling_group.app.desired_capacity == 2 && aws_autoscaling_group.app.max_size == 3
    error_message = "The lab must maintain two app nodes, bounded at three."
  }
  assert {
    condition     = !aws_instance.runner.associate_public_ip_address && !aws_launch_template.app.network_interfaces[0].associate_public_ip_address
    error_message = "Compute instances must not have public IPs."
  }
  assert {
    condition     = !aws_db_instance.medium.publicly_accessible && aws_db_instance.medium.storage_encrypted && aws_db_instance.medium.deletion_protection
    error_message = "Database must stay private, encrypted and protected from deletion."
  }
  assert {
    condition     = length(aws_subnet.public) == 2 && length(aws_subnet.app) == 2 && length(aws_efs_mount_target.medium) == 2
    error_message = "Both app AZs require network and EFS mount coverage."
  }
  assert {
    condition     = !aws_lb_target_group.app.stickiness[0].enabled && aws_autoscaling_group.app.health_check_type == "EC2"
    error_message = "Do not mask local sessions with stickiness or recycle the cluster on a shared outage."
  }
  assert {
    condition     = length(aws_elasticache_replication_group.medium) == 2 && alltrue([for r in aws_elasticache_replication_group.medium : r.transit_encryption_enabled && r.at_rest_encryption_enabled])
    error_message = "Session and MUC require separate encrypted Redis services."
  }
  assert {
    condition     = !strcontains(local.app_userdata, "install_database.php") && !strcontains(local.app_userdata, "upgrade.php")
    error_message = "App bootstrap must never run schema migrations."
  }
  assert {
    condition     = length(local.app_userdata) < 16384 && length(local.runner_userdata) < 16384
    error_message = "EC2 user-data must fit AWS's 16 KiB limit."
  }
}
