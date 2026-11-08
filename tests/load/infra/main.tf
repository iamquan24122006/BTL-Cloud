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
variable "expected_account" { type = string }
variable "project" { type = string }
variable "ami" { type = string }
variable "subnet" { type = string }
variable "stage_network_interface" { type = string }
variable "users_csv_arn" { type = string }
variable "results_arn" { type = string }
provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = var.project, Environment = "load-drill", Purpose = "private-load-generator", ManagedBy = "temporary-terraform" }
  }
}
data "aws_caller_identity" "current" {}
data "aws_subnet" "selected" { id = var.subnet }
resource "aws_iam_role" "generator" {
  name_prefix        = "${var.project}-loadgen-"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.generator.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_role_policy" "artifacts" {
  role = aws_iam_role.generator.name
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:GetObject"], Resource = [var.users_csv_arn, var.results_arn] },
    { Effect = "Allow", Action = ["s3:PutObject", "s3:AbortMultipartUpload"], Resource = var.results_arn }
  ] })
}
resource "aws_iam_instance_profile" "generator" {
  name_prefix = "${var.project}-loadgen-"
  role        = aws_iam_role.generator.name
}
resource "aws_security_group" "generator" {
  name_prefix = "${var.project}-loadgen-"
  description = "Temporary generator marker; SSM access only"
  vpc_id      = data.aws_subnet.selected.vpc_id
  ingress     = []
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_security_group" "stage_bridge" {
  name_prefix = "${var.project}-load-bridge-"
  description = "Temporary private TCP fixture; only this generator can connect"
  vpc_id      = data.aws_subnet.selected.vpc_id
  ingress {
    description     = "Private load generator only"
    from_port       = 8081
    to_port         = 8081
    protocol        = "tcp"
    security_groups = [aws_security_group.generator.id]
  }
  egress = []
}
resource "aws_network_interface_sg_attachment" "stage_bridge" {
  security_group_id    = aws_security_group.stage_bridge.id
  network_interface_id = var.stage_network_interface
}
resource "aws_instance" "generator" {
  ami                         = var.ami
  instance_type               = "t3.small"
  subnet_id                   = var.subnet
  vpc_security_group_ids      = [aws_security_group.generator.id]
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.generator.name
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    encrypted             = true
    delete_on_termination = true
  }
  credit_specification { cpu_credits = "standard" }
  tags = { Name = "${var.project}-load-generator" }
  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.current.account_id == var.expected_account
      error_message = "Wrong AWS account for load fixture"
    }
  }
  depends_on = [aws_iam_role_policy_attachment.ssm, aws_iam_role_policy.artifacts]
}
output "instance_id" { value = aws_instance.generator.id }
output "private_ip" { value = aws_instance.generator.private_ip }
output "stage_bridge_sg" { value = aws_security_group.stage_bridge.id }
