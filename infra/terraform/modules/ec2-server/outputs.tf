output "public_ip" {
  description = "Elastic IP address of the CloudSweep server"
  value       = aws_eip.server.public_ip
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.server.id
}

output "security_group_id" {
  description = "ID of the server security group"
  value       = aws_security_group.server.id
}
