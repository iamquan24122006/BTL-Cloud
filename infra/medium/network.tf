locals {
  name  = "${var.project}-${var.environment}-med"
  zones = { for i, az in var.availability_zones : az => i }
}
resource "aws_vpc" "medium" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = local.name }
}
resource "aws_internet_gateway" "medium" { vpc_id = aws_vpc.medium.id }
resource "aws_subnet" "public" {
  for_each                = local.zones
  vpc_id                  = aws_vpc.medium.id
  availability_zone       = each.key
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, each.value)
  map_public_ip_on_launch = false
  tags                    = { Name = "${local.name}-public-${each.key}" }
}
resource "aws_subnet" "app" {
  for_each                = local.zones
  vpc_id                  = aws_vpc.medium.id
  availability_zone       = each.key
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 10 + each.value)
  map_public_ip_on_launch = false
  tags                    = { Name = "${local.name}-app-${each.key}" }
}
resource "aws_subnet" "data" {
  for_each                = local.zones
  vpc_id                  = aws_vpc.medium.id
  availability_zone       = each.key
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 20 + each.value)
  map_public_ip_on_launch = false
  tags                    = { Name = "${local.name}-data-${each.key}" }
}
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.medium.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.medium.id
  }
}
resource "aws_route_table_association" "public" {
  for_each       = local.zones
  subnet_id      = aws_subnet.public[each.key].id
  route_table_id = aws_route_table.public.id
}
resource "aws_eip" "nat" { domain = "vpc" }
resource "aws_nat_gateway" "lab" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[var.availability_zones[0]].id
  depends_on    = [aws_internet_gateway.medium]
}
resource "aws_route_table" "app" {
  vpc_id = aws_vpc.medium.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.lab.id
  }
}
resource "aws_route_table_association" "app" {
  for_each       = local.zones
  subnet_id      = aws_subnet.app[each.key].id
  route_table_id = aws_route_table.app.id
}
resource "aws_route_table" "data" { vpc_id = aws_vpc.medium.id }
resource "aws_route_table_association" "data" {
  for_each       = local.zones
  subnet_id      = aws_subnet.data[each.key].id
  route_table_id = aws_route_table.data.id
}
resource "aws_security_group" "alb" {
  name_prefix = "${local.name}-alb-"
  vpc_id      = aws_vpc.medium.id
}
resource "aws_security_group" "app" {
  name_prefix = "${local.name}-app-"
  vpc_id      = aws_vpc.medium.id
}
resource "aws_security_group" "runner" {
  name_prefix = "${local.name}-runner-"
  vpc_id      = aws_vpc.medium.id
}
resource "aws_security_group" "db" {
  name_prefix = "${local.name}-db-"
  vpc_id      = aws_vpc.medium.id
}
resource "aws_security_group" "efs" {
  name_prefix = "${local.name}-efs-"
  vpc_id      = aws_vpc.medium.id
}
resource "aws_security_group" "redis" {
  name_prefix = "${local.name}-redis-"
  vpc_id      = aws_vpc.medium.id
}
resource "aws_vpc_security_group_ingress_rule" "public" {
  for_each          = var.frontend == "acm" ? toset(["80", "443"]) : toset([])
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = tonumber(each.value)
  to_port           = tonumber(each.value)
  ip_protocol       = "tcp"
}
resource "aws_vpc_security_group_egress_rule" "alb" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.app.id
  from_port                    = 8080
  to_port                      = 8080
  ip_protocol                  = "tcp"
}
resource "aws_vpc_security_group_ingress_rule" "app" {
  security_group_id            = aws_security_group.app.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 8080
  to_port                      = 8080
  ip_protocol                  = "tcp"
}
resource "aws_vpc_security_group_egress_rule" "compute" {
  for_each          = { app = aws_security_group.app.id, runner = aws_security_group.runner.id }
  security_group_id = each.value
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}
locals {
  data_access = {
    db_app       = { target = aws_security_group.db.id, source = aws_security_group.app.id, port = 5432 }
    db_runner    = { target = aws_security_group.db.id, source = aws_security_group.runner.id, port = 5432 }
    efs_app      = { target = aws_security_group.efs.id, source = aws_security_group.app.id, port = 2049 }
    efs_runner   = { target = aws_security_group.efs.id, source = aws_security_group.runner.id, port = 2049 }
    redis_app    = { target = aws_security_group.redis.id, source = aws_security_group.app.id, port = 6379 }
    redis_runner = { target = aws_security_group.redis.id, source = aws_security_group.runner.id, port = 6379 }
  }
}
resource "aws_vpc_security_group_ingress_rule" "data" {
  for_each                     = local.data_access
  security_group_id            = each.value.target
  referenced_security_group_id = each.value.source
  from_port                    = each.value.port
  to_port                      = each.value.port
  ip_protocol                  = "tcp"
}
