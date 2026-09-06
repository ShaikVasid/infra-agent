#!/usr/bin/env bash
# deploy.sh — Build, push to ECR, and deploy InfraBot to ECS Fargate
# Usage: bash deploy.sh
set -euo pipefail

REGION=$(terraform -chdir=terraform output -raw aws_region 2>/dev/null || echo "us-east-1")
ECR_URL=$(terraform -chdir=terraform output -raw ecr_repository_url 2>/dev/null || true)

# ── Step 1: Terraform init + apply (creates ECR if it doesn't exist yet) ──────
echo "==> [1/4] Running terraform init..."
terraform -chdir=terraform init -upgrade -input=false

echo "==> [2/4] Running terraform apply (ECR + ECS infrastructure)..."
terraform -chdir=terraform apply -auto-approve -input=false

# Re-read ECR URL after apply (in case this is the first run)
ECR_URL=$(terraform -chdir=terraform output -raw ecr_repository_url)
ACCOUNT_ID=$(echo "$ECR_URL" | cut -d'.' -f1)

echo ""
echo "ECR URL: $ECR_URL"

# ── Step 2: Authenticate Docker to ECR ────────────────────────────────────────
echo "==> [3/4] Logging Docker into ECR..."
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$ECR_URL"

# ── Step 3: Build and push image ──────────────────────────────────────────────
echo "==> [4/4] Building and pushing Docker image..."
docker build --platform linux/amd64 -t infrabot:latest .
docker tag infrabot:latest "$ECR_URL:latest"
docker push "$ECR_URL:latest"

# ── Step 4: Force ECS to pull the new image ───────────────────────────────────
CLUSTER=$(terraform -chdir=terraform output -raw ecs_cluster_name)
SERVICE=$(terraform -chdir=terraform output -raw ecs_service_name)

echo ""
echo "==> Forcing ECS service update to pull new image..."
aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --force-new-deployment \
  --region "$REGION" \
  --output text --query 'service.serviceName'

echo ""
echo "✅  Deploy triggered! ECS is pulling the new image."
echo ""
echo "==> To get the public IP once the task is RUNNING (~60s), run:"
echo ""
echo "    TASK_ARN=\$(aws ecs list-tasks --cluster $CLUSTER --service-name $SERVICE --region $REGION --query 'taskArns[0]' --output text)"
echo "    ENI=\$(aws ecs describe-tasks --cluster $CLUSTER --tasks \$TASK_ARN --region $REGION --query 'tasks[0].attachments[0].details[?name==\`networkInterfaceId\`].value' --output text)"
echo "    aws ec2 describe-network-interfaces --network-interface-ids \$ENI --region $REGION --query 'NetworkInterfaces[0].Association.PublicIp' --output text"
echo ""
echo "    Then open: http://<PUBLIC_IP>:8501"
