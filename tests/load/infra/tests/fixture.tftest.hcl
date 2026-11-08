mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = { account_id = "000000000000" }
  }
  mock_data "aws_subnet" {
    defaults = { vpc_id = "vpc-fixture" }
  }
}

variables {
  region                  = "ap-southeast-2"
  expected_account        = "000000000000"
  project                 = "moodle-fixture"
  ami                     = "ami-0123456789abcdef0"
  subnet                  = "subnet-fixture"
  stage_network_interface = "eni-fixture"
  users_csv_arn           = "arn:aws:s3:::fixture-backup/staging/load-users-private.csv"
  results_arn             = "arn:aws:s3:::fixture-backup/staging/load-run-fixture/*"
}

run "private_generator_and_scoped_access" {
  command = apply
  assert {
    condition     = length(aws_security_group.generator.ingress) == 0
    error_message = "The generator must have no ingress."
  }
  assert {
    condition = length(aws_security_group.stage_bridge.ingress) == 1 && alltrue([
      for rule in aws_security_group.stage_bridge.ingress :
      rule.protocol == "tcp" && rule.from_port == 8081 && rule.to_port == 8081 &&
      try(length(rule.cidr_blocks), 0) == 0 && try(length(rule.ipv6_cidr_blocks), 0) == 0 &&
      rule.security_groups == toset([aws_security_group.generator.id])
    ])
    error_message = "The bridge must accept only its dedicated generator SG on TCP 8081."
  }
  assert {
    condition     = aws_instance.generator.metadata_options[0].http_tokens == "required" && aws_instance.generator.root_block_device[0].encrypted && aws_instance.generator.credit_specification[0].cpu_credits == "standard"
    error_message = "Use IMDSv2, encrypted storage and standard CPU credits."
  }
  assert {
    condition     = jsondecode(aws_iam_role_policy.artifacts.policy).Statement[1].Resource == var.results_arn && !contains(jsondecode(aws_iam_role_policy.artifacts.policy).Statement[1].Action, "s3:DeleteObject")
    error_message = "The generator may write only its run prefix, without deleting backup objects."
  }
}
