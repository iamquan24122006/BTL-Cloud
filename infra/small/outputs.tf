output "instance_id" {
  value = aws_instance.moodle.id
}
output "ami_id" {
  value = data.aws_ami.ubuntu.id
}
output "region" {
  value = var.region
}
output "url_after_port_forward" {
  value = var.wwwroot
}
output "public_url" {
  value = var.public_url
}
output "backup_bucket" {
  value = var.backup_bucket
}
output "ssm_shell_command" {
  value = "aws --region ${var.region} ssm start-session --target ${aws_instance.moodle.id}"
}
