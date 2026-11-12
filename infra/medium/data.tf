resource "aws_db_subnet_group" "medium" {
  name_prefix = "${local.name}-"
  subnet_ids  = [for s in aws_subnet.data : s.id]
}
resource "aws_db_parameter_group" "medium" {
  name_prefix = "${local.name}-"
  family      = "postgres16"
  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "pending-reboot"
  }
}
resource "aws_db_instance" "medium" {
  identifier                  = local.name
  engine                      = "postgres"
  engine_version              = "16"
  instance_class              = var.db_instance_type
  allocated_storage           = var.db_allocated_storage
  storage_type                = "gp3"
  storage_encrypted           = true
  db_name                     = "moodle"
  username                    = "moodle_admin"
  manage_master_user_password = true
  db_subnet_group_name        = aws_db_subnet_group.medium.name
  vpc_security_group_ids      = [aws_security_group.db.id]
  parameter_group_name        = aws_db_parameter_group.medium.name
  publicly_accessible         = false
  multi_az                    = false
  backup_retention_period     = 7
  auto_minor_version_upgrade  = false
  deletion_protection         = true
  skip_final_snapshot         = false
  final_snapshot_identifier   = "${local.name}-final"
  copy_tags_to_snapshot       = true
}
resource "aws_efs_file_system" "medium" {
  encrypted        = true
  throughput_mode  = "bursting"
  performance_mode = "generalPurpose"
  tags             = { Name = local.name }
  lifecycle { prevent_destroy = true }
}
resource "aws_efs_mount_target" "medium" {
  for_each        = local.zones
  file_system_id  = aws_efs_file_system.medium.id
  subnet_id       = aws_subnet.data[each.key].id
  security_groups = [aws_security_group.efs.id]
}
resource "aws_efs_access_point" "medium" {
  file_system_id = aws_efs_file_system.medium.id
  posix_user {
    uid = 33
    gid = 33
  }
  root_directory {
    path = "/moodledata"
    creation_info {
      owner_uid   = 33
      owner_gid   = 33
      permissions = "0770"
    }
  }
}
resource "aws_efs_file_system_policy" "medium" {
  file_system_id = aws_efs_file_system.medium.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Deny", Principal = "*", Action = "elasticfilesystem:*", Resource = aws_efs_file_system.medium.arn
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
      }, {
      Effect    = "Allow", Principal = { AWS = [aws_iam_role.app.arn, aws_iam_role.runner.arn] }
      Action    = ["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite"]
      Resource  = aws_efs_file_system.medium.arn
      Condition = { StringEquals = { "elasticfilesystem:AccessPointArn" = aws_efs_access_point.medium.arn } }
    }]
  })
}
data "aws_secretsmanager_secret_version" "redis" {
  secret_id  = var.secrets.redis_arn
  version_id = var.secrets.redis_version
}
resource "aws_elasticache_subnet_group" "medium" {
  name       = local.name
  subnet_ids = [for s in aws_subnet.data : s.id]
}
# Separate servers isolate MUC flushes from sessions, both use logical DB 0.
resource "aws_elasticache_replication_group" "medium" {
  for_each                   = toset(["session", "cache"])
  replication_group_id       = "${substr(local.name, 0, 30)}-${each.key}"
  description                = "${local.name} ${each.key}; single-node lab, no automatic failover"
  engine                     = "redis"
  engine_version             = "7.1"
  parameter_group_name       = "default.redis7"
  node_type                  = var.redis_node_type
  num_cache_clusters         = 1
  automatic_failover_enabled = false
  multi_az_enabled           = false
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.medium.name
  security_group_ids         = [aws_security_group.redis.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = jsondecode(data.aws_secretsmanager_secret_version.redis.secret_string)["token"]
  snapshot_retention_limit   = 1
}
