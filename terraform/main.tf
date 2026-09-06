terraform {
  required_version = ">= 1.3"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── Data sources ──────────────────────────────────────────────────────────────
data "aws_caller_identity" "current" {}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ── ECR Repository ────────────────────────────────────────────────────────────
resource "aws_ecr_repository" "infrabot" {
  name                 = var.app_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "infrabot" {
  repository = aws_ecr_repository.infrabot.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 3 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 3
      }
      action = { type = "expire" }
    }]
  })
}

# ── ECS Cluster ───────────────────────────────────────────────────────────────
resource "aws_ecs_cluster" "infrabot" {
  name = var.app_name

  setting {
    name  = "containerInsights"
    value = "disabled"   # keep costs down for a portfolio project
  }
}

# ── CloudWatch Log Group ──────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "infrabot" {
  name              = "/ecs/${var.app_name}"
  retention_in_days = 7
}

# ── ECS Task Definition ───────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "infrabot" {
  family                   = var.app_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([{
    name  = var.app_name
    image = "${aws_ecr_repository.infrabot.repository_url}:latest"
    portMappings = [{
      containerPort = var.container_port
      protocol      = "tcp"
    }]
    environment = [
      { name = "GOOGLE_API_KEY",          value = var.google_api_key },
      { name = "AWS_ACCESS_KEY_ID",       value = var.aws_access_key_id },
      { name = "AWS_SECRET_ACCESS_KEY",   value = var.aws_secret_access_key },
      { name = "AWS_DEFAULT_REGION",      value = var.aws_region },
      { name = "STREAMLIT_SERVER_PORT",   value = tostring(var.container_port) },
      { name = "STREAMLIT_SERVER_HEADLESS", value = "true" },
      { name = "STREAMLIT_SERVER_ADDRESS",  value = "0.0.0.0" }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.infrabot.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
    essential = true
  }])
}

# ── Security Group ────────────────────────────────────────────────────────────
resource "aws_security_group" "infrabot" {
  name        = "${var.app_name}-sg"
  description = "Allow inbound traffic to InfraBot Streamlit UI"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Streamlit UI"
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound (AWS API calls, Gemini API)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ── ECS Service ───────────────────────────────────────────────────────────────
resource "aws_ecs_service" "infrabot" {
  name            = var.app_name
  cluster         = aws_ecs_cluster.infrabot.id
  task_definition = aws_ecs_task_definition.infrabot.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.infrabot.id]
    assign_public_ip = true   # task gets a public IP — no ALB needed
  }

  # Allow deployments to replace the running task
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
}
