mock_provider "aws" {}

variables {
  project     = "moodle-test"
  region      = "ap-southeast-2"
  bucket_name = "moodle-test-backup-fixture"
}

run "backup_is_private_encrypted_and_versioned" {
  command = plan
  assert {
    condition     = aws_s3_bucket_public_access_block.backup.block_public_acls && aws_s3_bucket_public_access_block.backup.block_public_policy && aws_s3_bucket_public_access_block.backup.ignore_public_acls && aws_s3_bucket_public_access_block.backup.restrict_public_buckets
    error_message = "Backup bucket must block every form of public access."
  }
  assert {
    condition     = aws_s3_bucket_versioning.backup.versioning_configuration[0].status == "Enabled"
    error_message = "Backup history must be versioned."
  }
  assert {
    condition     = one(aws_s3_bucket_server_side_encryption_configuration.backup.rule).apply_server_side_encryption_by_default[0].sse_algorithm == "AES256"
    error_message = "The small backup writer expects SSE-S3 encryption."
  }
  assert {
    condition     = !aws_s3_bucket.backup.force_destroy
    error_message = "Backup deletion must not silently remove stored backup sets."
  }
}
