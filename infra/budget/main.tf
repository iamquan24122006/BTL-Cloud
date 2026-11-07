terraform {
  required_version = ">= 1.13.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
variable "region" { type = string }
variable "billing_region" { type = string }
variable "expected_account" { type = string }
variable "project" { type = string }
variable "budget_name" { type = string }
variable "period_start" { type = string }
variable "period_end" { type = string }
variable "limit_usd" {
  type    = number
  default = 150
  validation {
    condition     = var.limit_usd > 0
    error_message = "Budget must be positive."
  }
}
provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = var.project, Purpose = "cost-monitoring", ReviewAfter = var.period_end }
  }
}
provider "aws" {
  alias  = "billing"
  region = var.billing_region
}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

resource "aws_sns_topic" "budget" {
  name = "${var.project}-budget-alerts"
}
resource "aws_sns_topic_policy" "budget" {
  arn = aws_sns_topic.budget.arn
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    {
      Sid = "BudgetPublisher", Effect = "Allow", Principal = { Service = "budgets.amazonaws.com" }, Action = "SNS:Publish", Resource = aws_sns_topic.budget.arn,
      Condition = {
        StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
        ArnLike      = { "aws:SourceArn" = "arn:${data.aws_partition.current.partition}:budgets::${data.aws_caller_identity.current.account_id}:*" }
      }
    },
    { Sid = "TLSOnly", Effect = "Deny", Principal = "*", Action = "SNS:Publish", Resource = aws_sns_topic.budget.arn, Condition = { Bool = { "aws:SecureTransport" = "false" } } }
  ] })
}
resource "aws_sqs_queue" "budget" {
  name                      = "${var.project}-budget-alerts"
  message_retention_seconds = 604800
  sqs_managed_sse_enabled   = true
}
resource "aws_sqs_queue_policy" "budget" {
  queue_url = aws_sqs_queue.budget.url
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    {
      Sid       = "TopicOnly", Effect = "Allow", Principal = { Service = "sns.amazonaws.com" }, Action = "sqs:SendMessage", Resource = aws_sqs_queue.budget.arn,
      Condition = { ArnEquals = { "aws:SourceArn" = aws_sns_topic.budget.arn }, StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id } }
    },
    { Sid = "TLSOnly", Effect = "Deny", Principal = "*", Action = "sqs:*", Resource = aws_sqs_queue.budget.arn, Condition = { Bool = { "aws:SecureTransport" = "false" } } }
  ] })
}
resource "aws_sns_topic_subscription" "budget" {
  topic_arn            = aws_sns_topic.budget.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.budget.arn
  raw_message_delivery = true
  depends_on           = [aws_sqs_queue_policy.budget]
}
resource "aws_budgets_budget" "monthly" {
  provider          = aws.billing
  account_id        = data.aws_caller_identity.current.account_id
  name              = var.budget_name
  budget_type       = "COST"
  limit_amount      = tostring(var.limit_usd)
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = var.period_start
  time_period_end   = var.period_end
  cost_types {
    include_credit = false
    include_refund = false
    use_amortized  = false
    use_blended    = false
  }
  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 75
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.budget.arn]
  }
  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
    notification_type         = "FORECASTED"
    subscriber_sns_topic_arns = [aws_sns_topic.budget.arn]
  }
  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.current.account_id == var.expected_account
      error_message = "Wrong AWS account for cost monitoring."
    }
  }
  depends_on = [aws_sns_topic_policy.budget, aws_sns_topic_subscription.budget]
}
output "topic_arn" { value = aws_sns_topic.budget.arn }
output "queue_url" { value = aws_sqs_queue.budget.url }
output "queue_arn" { value = aws_sqs_queue.budget.arn }
output "budget_name" { value = aws_budgets_budget.monthly.name }
