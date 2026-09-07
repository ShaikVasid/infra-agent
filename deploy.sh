#!/usr/bin/env bash
# deploy.sh — Build, push to ECR, and deploy InfraBot to ECS Fargate
# Usage: bash deploy.sh
set -euo pipefail

# ── Read region from tfvars using awk (works on macOS BSD) ────────────────────
REGION=$(awk -F'"' '/^aws_region/{print $2}' terraform/terraform.tfvars 2>/dev/null || true)
REGION=${REGION:-us-east-1}
echo "Region: $REGION"

# ── Step 1: Terraform init ─────────────────────────────────────────────────────
echo ""
echo "==> [1/4] terraform init..."
terraform -chdir=terraform init -upgrade -input=false

# ── Step 2: Terraform apply (creates ECR + ECS infra) ─────────────────────────
echo ""
echo "==> [2/4] terraform apply..."
terraform -chdir=terraform apply -auto-approve -input=false

# Read ECR URL from state AFTER apply succeeds
ECR_URL=$(terraform -chdir=terraform output -raw ecr_repository_url 2>/dev/null)
echo "ECR URL: $ECR_URL"

# ── Step 3: Authenticate Docker to ECR ────────────────────────────────────────
echo ""
echo "==> [3/4] Logging Docker into ECR..."
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$ECR_URL"

# ── Step 4: Build and push image ──────────────────────────────────────────────
echo ""
echo "==> [4/4] Building and pushing Docker image (linux/amd64)..."
docker build --platform linux/amd64 -t infrabot:latest .
docker tag infrabot:latest "$ECR_URL:latest"
docker push "$ECR_URL:latest"

# ── Step 5: Force ECS to pull the new image ───────────────────────────────────
CLUSTER=$(terraform -chdir=terraform output -raw ecs_cluster_name 2>/dev/null)
SERVICE=$(terraform -chdir=terraform output -raw ecs_service_name 2>/dev/null)

echo ""
echo "==> Forcing ECS service update..."
aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --force-new-deployment \
  --region "$REGION" \
  --output text --query 'service.serviceName'

echo ""
echo "✅  Deploy triggered! ECS is pulling the new image (~60s to start)."
echo ""
echo "==> Run these commands to get the public IP once the task is RUNNING:"
echo ""
echo "  TASK_ARN=\$(aws ecs list-tasks --cluster $CLUSTER --service-name $SERVICE --region $REGION --query 'taskArns[0]' --output text)"
echo "  ENI=\$(aws ecs describe-tasks --cluster $CLUSTER --tasks \$TASK_ARN --region $REGION --query 'tasks[0].attachments[0].details[?name==\`networkInterfaceId\`].value' --output text)"
echo "  aws ec2 describe-network-interfaces --network-interface-ids \$ENI --region $REGION --query 'NetworkInterfaces[0].Association.PublicIp' --output text"
echo ""
echo "Then open: http://<PUBLIC_IP>:8501"
