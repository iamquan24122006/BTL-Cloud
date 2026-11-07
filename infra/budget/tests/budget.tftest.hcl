mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = { account_id = "000000000000" }
  }
  mock_data "aws_partition" {
    defaults = { partition = "aws" }
  }
  mock_resource "aws_sns_topic" {
    defaults = { arn = "arn:aws:sns:ap-southeast-2:000000000000:moodle-fixture-budget-alerts" }
  }
  mock_resource "aws_sqs_queue" {
    defaults = {
      arn = "arn:aws:sqs:ap-southeast-2:000000000000:moodle-fixture-budget-alerts"
      url = "https://sqs.ap-southeast-2.amazonaws.com/000000000000/moodle-fixture-budget-alerts"
    }
  }
}
mock_provider "aws" {
  alias = "billing"
}
variables {
  region           = "ap-southeast-2"
  billing_region   = "us-east-1"
  expected_account = "000000000000"
  project          = "moodle-fixture"
  budget_name      = "moodle-fixture-monthly"
  period_start     = "2020-01-01_00:00"
  period_end       = "2087-01-01_00:00"
  limit_usd        = 150
}
run "budget_uses_internal_confirmed_channel" {
  command = apply
  assert {
    condition     = !aws_budgets_budget.monthly.cost_types[0].include_credit && aws_budgets_budget.monthly.limit_amount == "150"
    error_message = "Track gross usage against the revised 150 USD internal budget."
  }
  assert {
    condition     = aws_sns_topic_subscription.budget.protocol == "sqs" && aws_sns_topic_subscription.budget.raw_message_delivery && aws_sqs_queue.budget.sqs_managed_sse_enabled
    error_message = "Use the private encrypted queue channel, not an invented email recipient."
  }
  assert {
    condition     = jsondecode(aws_sns_topic_policy.budget.policy).Statement[0].Condition.StringEquals["aws:SourceAccount"] == var.expected_account && jsondecode(aws_sqs_queue_policy.budget.policy).Statement[0].Condition.ArnEquals["aws:SourceArn"] == aws_sns_topic.budget.arn
    error_message = "Scope the budget publisher to this account and queue delivery to this topic."
  }
}
