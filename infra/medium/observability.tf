resource "aws_cloudwatch_log_group" "medium" {
  name              = "/moodle/${local.name}"
  retention_in_days = 14
}
resource "aws_cloudwatch_metric_alarm" "cpu" {
  alarm_name          = "${local.name}-app-cpu"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  dimensions          = { AutoScalingGroupName = aws_autoscaling_group.app.name }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  comparison_operator = "GreaterThanThreshold"
  threshold           = 80
  alarm_actions       = [aws_sns_topic.operations.arn]
  ok_actions          = [aws_sns_topic.operations.arn]
}
resource "aws_cloudwatch_metric_alarm" "unhealthy" {
  alarm_name          = "${local.name}-unhealthy-targets"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "UnHealthyHostCount"
  dimensions          = { LoadBalancer = aws_lb.medium.arn_suffix, TargetGroup = aws_lb_target_group.app.arn_suffix }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 3
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  alarm_actions       = [aws_sns_topic.operations.arn]
  ok_actions          = [aws_sns_topic.operations.arn]
}
resource "aws_cloudwatch_metric_alarm" "errors" {
  alarm_name          = "${local.name}-target-5xx"
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  dimensions          = { LoadBalancer = aws_lb.medium.arn_suffix }
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 2
  comparison_operator = "GreaterThanThreshold"
  threshold           = 5
  alarm_actions       = [aws_sns_topic.operations.arn]
  ok_actions          = [aws_sns_topic.operations.arn]
  treat_missing_data  = "notBreaching"
}
resource "aws_cloudwatch_metric_alarm" "operations" {
  for_each            = { CronSuccess = 600, BackupSuccess = 90000 }
  alarm_name          = "${local.name}-${each.key}-missing"
  namespace           = "MoodleMedium"
  metric_name         = each.key
  dimensions          = { Site = local.name }
  statistic           = "Sum"
  period              = each.value
  evaluation_periods  = 1
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  alarm_actions       = [aws_sns_topic.operations.arn]
  ok_actions          = [aws_sns_topic.operations.arn]
  treat_missing_data  = "breaching"
}
resource "aws_cloudwatch_metric_alarm" "host" {
  for_each            = toset(["mem_used_percent", "disk_used_percent"])
  alarm_name          = "${local.name}-${each.key}"
  namespace           = "MoodleMedium"
  metric_name         = each.key
  dimensions          = { Site = local.name }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  comparison_operator = "GreaterThanThreshold"
  threshold           = 85
  alarm_actions       = [aws_sns_topic.operations.arn]
  ok_actions          = [aws_sns_topic.operations.arn]
}
resource "aws_cloudwatch_metric_alarm" "database" {
  for_each = {
    CPUUtilization   = { statistic = "Average", threshold = 80, comparison = "GreaterThanThreshold" }
    FreeStorageSpace = { statistic = "Minimum", threshold = 2147483648, comparison = "LessThanThreshold" }
    FreeableMemory   = { statistic = "Minimum", threshold = 104857600, comparison = "LessThanThreshold" }
  }
  alarm_name          = "${local.name}-db-${each.key}"
  namespace           = "AWS/RDS"
  metric_name         = each.key
  dimensions          = { DBInstanceIdentifier = aws_db_instance.medium.identifier }
  statistic           = each.value.statistic
  period              = 300
  evaluation_periods  = 2
  comparison_operator = each.value.comparison
  threshold           = each.value.threshold
  treat_missing_data  = "missing"
  alarm_actions       = [aws_sns_topic.operations.arn]
  ok_actions          = [aws_sns_topic.operations.arn]
}
resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  for_each            = aws_elasticache_replication_group.medium
  alarm_name          = "${local.name}-${each.key}-memory"
  namespace           = "AWS/ElastiCache"
  metric_name         = "DatabaseMemoryUsagePercentage"
  dimensions          = { CacheClusterId = "${each.value.replication_group_id}-001", CacheNodeId = "0001" }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  comparison_operator = "GreaterThanThreshold"
  threshold           = 80
  treat_missing_data  = "missing"
  alarm_actions       = [aws_sns_topic.operations.arn]
  ok_actions          = [aws_sns_topic.operations.arn]
}
resource "aws_cloudwatch_metric_alarm" "efs_io" {
  alarm_name          = "${local.name}-efs-io"
  namespace           = "AWS/EFS"
  metric_name         = "PercentIOLimit"
  dimensions          = { FileSystemId = aws_efs_file_system.medium.id }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  comparison_operator = "GreaterThanThreshold"
  threshold           = 80
  treat_missing_data  = "missing"
  alarm_actions       = [aws_sns_topic.operations.arn]
  ok_actions          = [aws_sns_topic.operations.arn]
}
resource "aws_cloudwatch_metric_alarm" "runner_cpu" {
  alarm_name          = "${local.name}-runner-cpu"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  dimensions          = { InstanceId = aws_instance.runner.id }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  comparison_operator = "GreaterThanThreshold"
  threshold           = 80
  treat_missing_data  = "missing"
  alarm_actions       = [aws_sns_topic.operations.arn]
  ok_actions          = [aws_sns_topic.operations.arn]
}
