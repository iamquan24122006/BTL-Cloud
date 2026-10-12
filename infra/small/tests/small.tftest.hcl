mock_provider "aws" {
  mock_data "aws_ami" {
    defaults = {
      id = "ami-0123456789abcdef0"
    }
  }
}

variables {
  project        = "moodle-test"
  environment    = "dev"
  region         = "ap-southeast-1"
  size           = "small"
  instance_type  = "t3.medium"
  volume_gib     = 30
  moodle_version = "4.5.15"
  wwwroot        = "http://localhost:8080"
  backup_bucket  = ""
  tags           = {}
}

run "small_security_and_payload" {
  command = plan
  assert {
    condition     = length(aws_security_group.lab.ingress) == 0
    error_message = "The small lab must not expose an inbound port."
  }
  assert {
    condition     = aws_instance.moodle.metadata_options[0].http_tokens == "required"
    error_message = "IMDSv2 must be required."
  }
  assert {
    condition     = aws_instance.moodle.root_block_device[0].encrypted
    error_message = "The Moodle data volume must be encrypted."
  }
  assert {
    condition     = length(aws_instance.moodle.user_data_base64) <= 21844
    error_message = "Compressed user-data must fit the EC2 16 KiB limit."
  }
  assert {
    condition     = length(aws_iam_role_policy.backup) == 0
    error_message = "Do not grant S3 rights when no backup bucket is configured."
  }
}

run "backup_permission_is_scoped" {
  command = plan
  variables {
    backup_bucket = "example-moodle-backup"
  }
  assert {
    condition     = jsondecode(aws_iam_role_policy.backup[0].policy).Statement[0].Resource == "arn:aws:s3:::example-moodle-backup/moodle-test-dev/*"
    error_message = "Backup access must be scoped to the configured bucket and environment prefix."
  }
  assert {
    condition     = !contains(jsondecode(aws_iam_role_policy.backup[0].policy).Statement[0].Action, "s3:DeleteObject")
    error_message = "The application role must not delete remote backups."
  }
}
