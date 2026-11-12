terraform {
  required_version = ">= 1.10.0, < 2.0.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  backend "local" {}
}
variable "region" { type = string }
variable "account_id" { type = string }
variable "project" { type = string }
variable "environment" { type = string }
variable "base_ami" { type = string }
variable "bake" {
  type = object({
    awscli_version = string, awscli_sha256 = string,
    cloudwatch_url = string, cloudwatch_sha256 = string,
    efs_version    = string, efs_commit = string, efs_deb_url = string, efs_deb_sha256 = string
  })
}
provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
  default_tags {
    tags = { Project = var.project, Environment = var.environment, Owner = "N2", Purpose = "medium-ami-builder" }
  }
}
locals {
  name = "${var.project}-${var.environment}-builder"
  config = {
    write_files = [
      { path = "/opt/moodle-builder/bake-host.sh", owner = "root:root", permissions = "0750", encoding = "b64", content = filebase64("${path.module}/../../scripts/medium/bake-host.sh") },
      { path = "/opt/moodle-builder/bake.json", owner = "root:root", permissions = "0600", encoding = "b64", content = base64encode(jsonencode(var.bake)) }
    ]
    runcmd = [["bash", "/opt/moodle-builder/bake-host.sh"]]
  }
}
resource "aws_vpc" "builder" {
  cidr_block           = "10.44.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = local.name }
}
resource "aws_subnet" "builder" {
  vpc_id                  = aws_vpc.builder.id
  cidr_block              = "10.44.1.0/24"
  map_public_ip_on_launch = false
}
resource "aws_internet_gateway" "builder" { vpc_id = aws_vpc.builder.id }
resource "aws_route_table" "builder" {
  vpc_id = aws_vpc.builder.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.builder.id
  }
}
resource "aws_route_table_association" "builder" {
  subnet_id      = aws_subnet.builder.id
  route_table_id = aws_route_table.builder.id
}
resource "aws_security_group" "builder" {
  vpc_id      = aws_vpc.builder.id
  name_prefix = "${local.name}-"
  ingress     = []
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_iam_role" "builder" {
  name_prefix = "${local.name}-"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.builder.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_instance_profile" "builder" {
  name_prefix = "${local.name}-"
  role        = aws_iam_role.builder.name
}
resource "aws_instance" "builder" {
  ami                         = var.base_ami
  instance_type               = "t3.medium"
  subnet_id                   = aws_subnet.builder.id
  vpc_security_group_ids      = [aws_security_group.builder.id]
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.builder.name
  user_data_base64            = base64gzip("#cloud-config\n${yamlencode(local.config)}")
  user_data_replace_on_change = true
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
  root_block_device {
    volume_type = "gp3"
    volume_size = 30
    encrypted   = true
  }
  tags       = { Name = local.name }
  depends_on = [aws_route_table_association.builder, aws_iam_role_policy_attachment.ssm]
}
output "instance_id" { value = aws_instance.builder.id }
output "base_ami" { value = var.base_ami }
