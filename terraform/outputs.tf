output "ecr_repository_url" {
  description = "ECR repository URL — use this in deploy.sh to tag and push the Docker image"
  value       = aws_ecr_repository.infrabot.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.infrabot.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.infrabot.name
}

output "aws_region" {
  description = "AWS region where InfraBot is deployed"
  value       = var.aws_region
}

output "how_to_get_public_ip" {
  description = "Instructions to find the running task's public IP"
  value       = <<-EOT
    Run this command to get the public IP of the running task:

      TASK_ARN=$(aws ecs list-tasks \
        --cluster ${aws_ecs_cluster.infrabot.name} \
        --service-name ${aws_ecs_service.infrabot.name} \
        --region ${var.aws_region} \
        --query 'taskArns[0]' --output text)

      aws ecs describe-tasks \
        --cluster ${aws_ecs_cluster.infrabot.name} \
        --tasks $TASK_ARN \
        --region ${var.aws_region} \
        --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
        --output text | xargs -I{} aws ec2 describe-network-interfaces \
        --network-interface-ids {} \
        --region ${var.aws_region} \
        --query 'NetworkInterfaces[0].Association.PublicIp' \
        --output text

    Then open: http://<PUBLIC_IP>:8501
  EOT
}
