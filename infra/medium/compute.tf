locals {
  trust_ec2 = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
  runtime = {
    region                = var.region
    name                  = local.name
    wwwroot               = local.public_url
    artifact              = var.artifact
    backup_bucket         = var.backup_bucket
    restore_source_prefix = var.restore_source_prefix
    db_host               = aws_db_instance.medium.address
    db_name               = "moodle"
    efs_id                = aws_efs_file_system.medium.id
    access_point          = aws_efs_access_point.medium.id
    session_host          = aws_elasticache_replication_group.medium["session"].primary_endpoint_address
    cache_host            = aws_elasticache_replication_group.medium["cache"].primary_endpoint_address
    secrets               = var.secrets
    log_group             = aws_cloudwatch_log_group.medium.name
  }
  app_userdata = templatefile("${path.module}/user-data.sh.tftpl", {
    region = var.region, bucket = var.artifact.bucket, key = var.artifact.key,
    sha256 = var.artifact.sha256, config = base64encode(jsonencode(merge(local.runtime, { role = "app" })))
  })
  runner_userdata = templatefile("${path.module}/user-data.sh.tftpl", {
    region = var.region, bucket = var.artifact.bucket, key = var.artifact.key,
    sha256 = var.artifact.sha256, config = base64encode(jsonencode(merge(local.runtime, {
      role = "runner", master_secret_arn = aws_db_instance.medium.master_user_secret[0].secret_arn
    })))
  })
}
resource "aws_iam_role" "app" {
  name_prefix        = "${substr(local.name, 0, 26)}-app-"
  assume_role_policy = local.trust_ec2
}
resource "aws_iam_role" "runner" {
  name_prefix        = "${substr(local.name, 0, 26)}-runner-"
  assume_role_policy = local.trust_ec2
}
resource "aws_iam_role_policy_attachment" "ssm" {
  for_each   = { app = aws_iam_role.app.name, runner = aws_iam_role.runner.name }
  role       = each.value
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_role_policy" "runtime" {
  for_each = { app = aws_iam_role.app.id, runner = aws_iam_role.runner.id }
  role     = each.value
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat([
      { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
      { Effect = "Allow", Action = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"], Resource = "arn:aws:ecr:${var.region}:${var.account_id}:repository/${split("@", split("amazonaws.com/", var.artifact.image)[1])[0]}" },
      { Effect = "Allow", Action = ["s3:GetObject"], Resource = "arn:aws:s3:::${var.artifact.bucket}/${var.artifact.key}" },
      { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = concat([var.secrets.runtime_arn, var.secrets.redis_arn], each.key == "runner" ? [var.secrets.migration_arn, aws_db_instance.medium.master_user_secret[0].secret_arn] : []) },
      { Effect = "Allow", Action = ["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite"], Resource = aws_efs_file_system.medium.arn, Condition = { StringEquals = { "elasticfilesystem:AccessPointArn" = aws_efs_access_point.medium.arn } } },
      { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams"], Resource = "${aws_cloudwatch_log_group.medium.arn}:*" },
      { Effect = "Allow", Action = ["cloudwatch:PutMetricData"], Resource = "*", Condition = { StringEquals = { "cloudwatch:namespace" = "MoodleMedium" } } }
      ], [for statement in [
        { Effect = "Allow", Action = ["s3:PutObject", "s3:AbortMultipartUpload"], Resource = "arn:aws:s3:::${var.backup_bucket}/${local.name}/*" },
        { Effect = "Allow", Action = ["s3:GetObject"], Resource = [for prefix in distinct(compact([local.name, var.restore_source_prefix])) : "arn:aws:s3:::${var.backup_bucket}/${prefix}/*"] },
        { Effect = "Allow", Action = ["s3:ListBucket"], Resource = "arn:aws:s3:::${var.backup_bucket}", Condition = { StringLike = { "s3:prefix" = [for prefix in distinct(compact([local.name, var.restore_source_prefix])) : "${prefix}/*"] } } },
        { Effect = "Allow", Action = ["ec2:DescribeInstances", "ssm:ListCommandInvocations", "ssm:GetCommandInvocation"], Resource = "*" },
        { Effect = "Allow", Action = ["ssm:SendCommand"], Resource = "arn:aws:ssm:${var.region}::document/AWS-RunShellScript" },
        { Effect = "Allow", Action = ["ssm:SendCommand"], Resource = "arn:aws:ec2:${var.region}:${var.account_id}:instance/*", Condition = { StringEquals = { "ssm:resourceTag/Name" = "${local.name}-app" } } }
    ] : statement if each.key == "runner"])
  })
}
resource "aws_iam_instance_profile" "app" {
  name_prefix = "${local.name}-app-"
  role        = aws_iam_role.app.name
}
resource "aws_iam_instance_profile" "runner" {
  name_prefix = "${local.name}-runner-"
  role        = aws_iam_role.runner.name
}
resource "aws_launch_template" "app" {
  name_prefix   = "${local.name}-"
  image_id      = var.ami_id
  instance_type = var.instance_type
  user_data     = base64encode(local.app_userdata)
  iam_instance_profile { name = aws_iam_instance_profile.app.name }
  network_interfaces {
    associate_public_ip_address = false
    security_groups             = [aws_security_group.app.id]
    delete_on_termination       = true
  }
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
  block_device_mappings {
    device_name = "/dev/sda1"
    ebs {
      volume_size           = var.volume_gib
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }
  tag_specifications {
    resource_type = "instance"
    tags          = { Name = "${local.name}-app", Release = var.artifact.release }
  }
}
resource "aws_autoscaling_group" "app" {
  name                = "${local.name}-app"
  min_size            = 2
  desired_capacity    = 2
  max_size            = 3
  vpc_zone_identifier = [for s in aws_subnet.app : s.id]
  target_group_arns   = [aws_lb_target_group.app.arn]
  # Shared DB/EFS/cache failures must not cause a replacement storm.
  # ALB gates traffic; ASG replaces EC2 failures. Investigate unhealthy apps via logs/SSM.
  health_check_type         = "EC2"
  health_check_grace_period = 600
  launch_template {
    id      = aws_launch_template.app.id
    version = tostring(aws_launch_template.app.latest_version)
  }
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
      instance_warmup        = 300
    }
  }
  depends_on = [aws_efs_mount_target.medium, aws_efs_file_system_policy.medium, aws_route_table_association.app, aws_iam_role_policy.runtime, aws_lb_listener.http, aws_lb_listener.https]
}
resource "aws_instance" "runner" {
  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.app[var.availability_zones[0]].id
  associate_public_ip_address = false
  vpc_security_group_ids      = [aws_security_group.runner.id]
  iam_instance_profile        = aws_iam_instance_profile.runner.name
  user_data_base64            = base64encode(local.runner_userdata)
  user_data_replace_on_change = true
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
  root_block_device {
    encrypted   = true
    volume_type = "gp3"
    volume_size = var.volume_gib
  }
  tags       = { Name = "${local.name}-runner", Release = var.artifact.release }
  depends_on = [aws_efs_mount_target.medium, aws_efs_file_system_policy.medium, aws_route_table_association.app, aws_iam_role_policy.runtime]
}
