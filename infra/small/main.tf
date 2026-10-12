locals {
  name = "${var.project}-${var.environment}"
  scripts = {
    "bootstrap.sh"       = "0750"
    "configure.php"      = "0644"
    "install-db.php"     = "0644"
    "backup.sh"          = "0750"
    "health.sh"          = "0750"
    "setup-host.sh"      = "0750"
    "php-cli.sh"         = "0750"
    "moodle-web.sh"      = "0750"
    "Dockerfile"         = "0644"
    "moodle.ini"         = "0644"
    "moodle-apache.conf" = "0644"
  }
  cloud_config = {
    write_files = concat([
      for name, mode in local.scripts : {
        path        = "/opt/moodle-distribution/${name}"
        owner       = "root:root"
        permissions = mode
        encoding    = "b64"
        content     = filebase64("${path.module}/../../scripts/${name}")
      }
      ], [{
        path        = "/etc/moodle/deploy.json"
        owner       = "root:root"
        permissions = "0600"
        encoding    = "b64"
        content = base64encode(jsonencode({
          moodle_version = var.moodle_version
          wwwroot        = var.wwwroot
          backup_bucket  = var.backup_bucket
          backup_prefix  = local.name
          region         = var.region
        }))
    }])
    runcmd = [["bash", "/opt/moodle-distribution/bootstrap.sh"]]
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical official publisher, not the deployment account.
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-resolute-26.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_vpc" "lab" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = local.name }
}
resource "aws_subnet" "lab" {
  vpc_id                  = aws_vpc.lab.id
  cidr_block              = "10.42.1.0/24"
  map_public_ip_on_launch = true
  tags                    = { Name = "${local.name}-public" }
}
resource "aws_internet_gateway" "lab" {
  vpc_id = aws_vpc.lab.id
}
resource "aws_route_table" "lab" {
  vpc_id = aws_vpc.lab.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.lab.id
  }
}
resource "aws_route_table_association" "lab" {
  subnet_id      = aws_subnet.lab.id
  route_table_id = aws_route_table.lab.id
}
resource "aws_security_group" "lab" {
  name_prefix = "${local.name}-"
  description = "No inbound ports; SSM only. Outbound for packages and AWS APIs."
  vpc_id      = aws_vpc.lab.id
  ingress     = []
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_iam_role" "ec2" {
  name_prefix = "${local.name}-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_role_policy" "backup" {
  count = var.backup_bucket == "" ? 0 : 1
  role  = aws_iam_role.ec2.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:AbortMultipartUpload"]
      Resource = "arn:aws:s3:::${var.backup_bucket}/${local.name}/*"
    }]
  })
}
resource "aws_iam_instance_profile" "ec2" {
  name_prefix = "${local.name}-"
  role        = aws_iam_role.ec2.name
}
resource "aws_instance" "moodle" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.lab.id
  vpc_security_group_ids      = [aws_security_group.lab.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2.name
  associate_public_ip_address = true
  user_data_base64            = base64gzip("#cloud-config\n${yamlencode(local.cloud_config)}")
  user_data_replace_on_change = true
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.volume_gib
    encrypted             = true
    delete_on_termination = true
  }
  credit_specification {
    cpu_credits = "standard"
  }
  tags       = { Name = local.name }
  depends_on = [aws_route_table_association.lab, aws_iam_role_policy_attachment.ssm, aws_iam_role_policy.backup]
}
