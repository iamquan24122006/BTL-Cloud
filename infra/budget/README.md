# Budget and internal alert channel

Monitoring-only cost budget, SNS topic and private SSE-SQS queue. The default limit is **150 USD**. It tracks account-wide unblended usage before credits/refunds, with ACTUAL >75% and FORECASTED >100% notifications. It does not stop resources or guarantee a hard spending limit.

Use the project region for SNS/SQS and a separate `billing_region` for the global Budgets API endpoint. This lab uses Sydney for notifications and us-east-1 for billing. Same-account SNS topic permissions follow [AWS's Budgets guidance](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-sns-policy.html), scoped with SourceAccount and SourceArn. The queue accepts SNS delivery only from this topic and retains messages for seven days.

Supply `expected_account`, `project`, `budget_name`, `period_start`, `period_end`, `region`, `billing_region` and `limit_usd` in a private variable file. Period format is `YYYY-MM-DD_HH:MM`. Keep separate private Terraform state, review the plan, then apply. CI uses mocked providers, including the billing alias; no budget or queue is created in CI.

The 150 USD limit is for the whole project. A monthly budget covers only its configured period. Keep a cumulative ledger across months and reduce any renewed budget by prior project spending. The current lab budget is configured only through the end of its recorded monthly period; renewal requires reviewing the ledger.

## Receiving alerts

There is no email recipient. An authorized operator reads the queue through the AWS console or CLI using `queue_url` from Terraform outputs. Check within the seven-day retention period and record alerts in the cost ledger. A future email subscription needs an actual authorized recipient and confirmation.

For channel verification, confirm that the topic has exactly the intended SQS subscription, publish a nonce-tagged synthetic delivery test, receive the same nonce and acknowledge only that test message. This checks SNS → SQS transport; it does not prove that a real budget threshold has been exceeded. Do not manufacture billing activity to trigger a threshold.

## Ownership and cleanup

Keep this monitor when temporary load/install machines are destroyed. Its budget period and `ReviewAfter` tags identify the review deadline. At project cleanup, review a destroy plan for this module's state separately from application and backup states. SNS/SQS request charges, if any, are separate from EC2/EBS estimates; see [AWS Budgets pricing](https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/) and the actual account ledger.
