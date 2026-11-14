# Alarm messages contain resource/metric metadata only. The durable inbox uses SSE-SQS.
# Operators may add a confirmed email subscription to this topic without exposing credentials.
resource "aws_sns_topic" "operations" {
  name = "${local.name}-operations"
}
resource "aws_sns_topic_policy" "operations" {
  arn = aws_sns_topic.operations.arn
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    {
      Sid = "SiteAlarmsOnly", Effect = "Allow", Principal = { Service = "cloudwatch.amazonaws.com" }, Action = "sns:Publish", Resource = aws_sns_topic.operations.arn,
      Condition = {
        StringEquals = { "aws:SourceAccount" = var.account_id }
        ArnLike      = { "aws:SourceArn" = "arn:aws:cloudwatch:${var.region}:${var.account_id}:alarm:${local.name}-*" }
      }
    },
    { Sid = "TLSOnly", Effect = "Deny", Principal = "*", Action = "sns:Publish", Resource = aws_sns_topic.operations.arn, Condition = { Bool = { "aws:SecureTransport" = "false" } } }
  ] })
}
resource "aws_sqs_queue" "operations" {
  name                      = "${local.name}-operations"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}
resource "aws_sqs_queue_policy" "operations" {
  queue_url = aws_sqs_queue.operations.url
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    {
      Sid       = "SiteTopicOnly", Effect = "Allow", Principal = { Service = "sns.amazonaws.com" }, Action = "sqs:SendMessage", Resource = aws_sqs_queue.operations.arn,
      Condition = { ArnEquals = { "aws:SourceArn" = aws_sns_topic.operations.arn }, StringEquals = { "aws:SourceAccount" = var.account_id } }
    },
    { Sid = "TLSOnly", Effect = "Deny", Principal = "*", Action = "sqs:*", Resource = aws_sqs_queue.operations.arn, Condition = { Bool = { "aws:SecureTransport" = "false" } } }
  ] })
}
resource "aws_sns_topic_subscription" "operations" {
  topic_arn            = aws_sns_topic.operations.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.operations.arn
  raw_message_delivery = true
  depends_on           = [aws_sqs_queue_policy.operations]
}

# An isolated metric exercises evaluation -> SNS -> inbox -> recovery without
# setting the state of a production health/scaling alarm or disrupting users.
resource "aws_cloudwatch_metric_alarm" "delivery_probe" {
  alarm_name          = "${local.name}-notification-probe"
  alarm_description   = "Operator test only: emit NotificationProbe=1 then 0; inspect both transitions in the operations inbox."
  namespace           = "MoodleMedium"
  metric_name         = "NotificationProbe"
  dimensions          = { Site = local.name }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.operations.arn]
  ok_actions          = [aws_sns_topic.operations.arn]
  depends_on          = [aws_sns_topic_policy.operations, aws_sns_topic_subscription.operations]
}
