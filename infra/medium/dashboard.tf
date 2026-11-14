locals {
  operational_alarm_arns = concat(
    [aws_cloudwatch_metric_alarm.cpu.arn, aws_cloudwatch_metric_alarm.unhealthy.arn, aws_cloudwatch_metric_alarm.errors.arn,
    aws_cloudwatch_metric_alarm.efs_io.arn, aws_cloudwatch_metric_alarm.runner_cpu.arn],
    [for a in aws_cloudwatch_metric_alarm.operations : a.arn],
    [for a in aws_cloudwatch_metric_alarm.host : a.arn],
    [for a in aws_cloudwatch_metric_alarm.database : a.arn],
    [for a in aws_cloudwatch_metric_alarm.redis_memory : a.arn]
  )
  dashboard_metrics = [
    { title = "ALB latency (p95 seconds)", stat = "p95", metrics = [["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", aws_lb.medium.arn_suffix]] },
    { title = "ALB requests and target errors", stat = "Sum", metrics = [["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.medium.arn_suffix], ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", aws_lb.medium.arn_suffix]] },
    { title = "Healthy targets and desired apps (2-3)", stat = "Average", metrics = [["AWS/ApplicationELB", "HealthyHostCount", "LoadBalancer", aws_lb.medium.arn_suffix, "TargetGroup", aws_lb_target_group.app.arn_suffix], ["AWS/AutoScaling", "GroupDesiredCapacity", "AutoScalingGroupName", aws_autoscaling_group.app.name]] },
    { title = "App / runner CPU (%)", stat = "Average", metrics = [["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", aws_autoscaling_group.app.name], ["AWS/EC2", "CPUUtilization", "InstanceId", aws_instance.runner.id]] },
    { title = "RDS CPU (%)", stat = "Average", metrics = [["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", aws_db_instance.medium.identifier]] },
    { title = "RDS free memory / disk (bytes)", stat = "Minimum", metrics = [["AWS/RDS", "FreeableMemory", "DBInstanceIdentifier", aws_db_instance.medium.identifier], ["AWS/RDS", "FreeStorageSpace", "DBInstanceIdentifier", aws_db_instance.medium.identifier]] },
    { title = "Redis memory (%)", stat = "Maximum", metrics = [for r in aws_elasticache_replication_group.medium : ["AWS/ElastiCache", "DatabaseMemoryUsagePercentage", "CacheClusterId", "${r.replication_group_id}-001", "CacheNodeId", "0001"]] },
    { title = "EFS IO limit (%)", stat = "Maximum", metrics = [["AWS/EFS", "PercentIOLimit", "FileSystemId", aws_efs_file_system.medium.id]] },
    { title = "Host memory / disk (%)", stat = "Maximum", metrics = [["MoodleMedium", "mem_used_percent", "Site", local.name], ["MoodleMedium", "disk_used_percent", "Site", local.name]] },
    { title = "Runner cron / backup successes", stat = "Sum", metrics = [["MoodleMedium", "CronSuccess", "Site", local.name], ["MoodleMedium", "BackupSuccess", "Site", local.name]] }
  ]
}
resource "aws_cloudwatch_dashboard" "medium" {
  dashboard_name = "${local.name}-operations"
  dashboard_body = jsonencode({ widgets = concat(
    [{ type = "alarm", x = 0, y = 0, width = 24, height = 3, properties = { title = "Medium operational alarms", alarms = local.operational_alarm_arns } }],
    [for i, w in local.dashboard_metrics : {
      type       = "metric", x = (i % 2) * 12, y = 3 + floor(i / 2) * 6, width = 12, height = 6,
      properties = { title = w.title, region = var.region, view = "timeSeries", stat = w.stat, period = 300, metrics = w.metrics }
    }]
  ) })
}
