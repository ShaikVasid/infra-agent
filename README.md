# InfraBot 🤖

An AI-powered DevOps agent that connects to live **AWS** and **GCP** infrastructure and lets you inspect, audit, and get security advice through plain English — no cloud console, no complex CLI commands needed.

Built with **LangGraph**, **Google Gemini**, and **boto3/google-cloud** SDKs.

---

## ✨ Features

- 🔍 **Multi-cloud support** — audits both AWS and GCP in one command
- 🔐 **Security auditing** — flags public S3/GCS buckets, wildcard IAM permissions, open security groups
- 🗺️ **Terraform plan analysis** — paste a `terraform plan` JSON and get a risk summary
- 📋 **CloudWatch log fetching** — pull recent logs from any log group in plain English
- 🧠 **ReAct reasoning loop** — chains multiple tool calls to produce comprehensive reports
- 💬 **Session memory** — follow-up questions work without repeating context
- 🌐 **Streamlit web UI** — browser-based chat interface (plus a CLI option)

---

## 🛠️ Tool Inventory (10 Tools)

| Tool | Cloud | What it does |
|------|-------|-------------|
| `list_s3_buckets` | AWS | Lists all S3 buckets, flags public ones |
| `check_s3_bucket_details` | AWS | Checks versioning & encryption on a bucket |
| `list_iam_roles` | AWS | Lists all IAM roles in the account |
| `analyze_iam_role` | AWS | Audits a role for wildcard (*) permissions |
| `list_ec2_instances` | AWS | Lists EC2 virtual servers by region |
| `parse_terraform_plan` | AWS | Scans terraform plan JSON for security risks |
| `fetch_cloudwatch_logs` | AWS | Fetches recent logs from a CloudWatch log group |
| `list_gcs_buckets` | GCP ✨ | Lists GCS buckets, checks public access |
| `list_gcp_iam_bindings` | GCP ✨ | Lists IAM bindings, flags allUsers exposure |
| `multi_cloud_audit` | Both ✨ | Full security audit across AWS + GCP |

---

## 🏗️ Architecture

```
User message
     │
     ▼
┌─────────────────────────────┐
│  LangGraph ReAct Loop       │
│  ┌─────────────────────┐   │
│  │  Google Gemini LLM  │   │  ← Thinks, decides which tools to call
│  └─────────────────────┘   │
│           │                 │
│    ┌──────┴──────┐          │
│    ▼             ▼          │
│  AWS Tools    GCP Tools     │  ← boto3 / google-cloud SDKs
│  (boto3)     (google-cloud) │
└─────────────────────────────┘
     │
     ▼
Plain-English answer
```

**ReAct pattern**: Reason → Act (call a tool) → Observe the result → Reason again → Answer

---

## 📁 Project Structure

```
infra-agent/
├── .env                    ← API keys (never committed)
├── .env.example            ← Template showing required keys
├── .gitignore
├── requirements.txt
├── main.py                 ← CLI entry point
├── agent/
│   ├── agent.py            ← LangGraph ReAct agent + memory
│   └── tools/
│       ├── aws_tools.py    ← 7 AWS tool functions
│       └── gcp_tools.py    ← 3 GCP tool functions
└── ui/
    └── app.py              ← Streamlit web UI
```

---

## ⚙️ Setup

### Prerequisites

- Python 3.10+
- A **Google Gemini** API key — free at [aistudio.google.com](https://aistudio.google.com)
- **AWS** IAM user with read-only credentials (Access Key ID + Secret)
- *(Optional)* **GCP** service account JSON for GCP tools

### Install

```bash
git clone https://github.com/vasidshaik995/infra-agent.git
cd infra-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and fill in your API keys
```

### Configure `.env`

```env
GOOGLE_API_KEY=your_gemini_key_here
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_DEFAULT_REGION=us-east-1

# GCP (optional — needed for GCP tools)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

---

## 🚀 Running InfraBot

### Web UI (recommended)

```bash
source venv/bin/activate
streamlit run ui/app.py
# Opens at http://localhost:8501
```

### CLI

```bash
source venv/bin/activate
python main.py
```

---

## 💬 Example Prompts

```
list my S3 buckets
audit my full AWS infrastructure
analyze the AdministratorAccess IAM role
list my GCS buckets
run a multi-cloud security audit
fetch the last 20 logs from /aws/lambda/my-function
show me EC2 instances in eu-west-1
```

---

## 🔒 Security Design

- **Read-only AWS credentials** — InfraBot cannot modify, delete, or create any resources
- **`.env` never committed** — `.gitignore` explicitly excludes it
- **Minimal IAM permissions** — only the APIs the tools actually use
- **Local execution** — data only goes to the LLM API (Gemini) and the cloud APIs

---

## 🗺️ Roadmap

- [x] Day 1 — AWS tools (S3, IAM, EC2), ReAct agent, CLI
- [x] Day 2 — Streamlit UI, Terraform plan parser, CloudWatch log fetcher
- [x] Day 3 — GCP tools, multi-cloud audit, README
- [x] Day 4–5 — Dockerise with Dockerfile + docker-compose
- [x] Day 6–7 — Deploy on AWS ECS Fargate via Terraform
- [x] Day 8–10 — GitHub Actions CI/CD pipeline (build → ECR → ECS deploy on every push to main)

---

## 🧰 Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Framework | LangGraph (ReAct agent) |
| LLM | Google Gemini (via LangChain) |
| AWS SDK | boto3 |
| GCP SDK | google-cloud-storage, google-cloud-resource-manager |
| Web UI | Streamlit |
| Memory | LangGraph MemorySaver |
