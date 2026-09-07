"""
AWS tools for InfraBot.
Each function is a LangChain tool the agent can call.
Day 1: S3 + IAM basics. More tools added in later days.
"""
import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from langchain_core.tools import tool


def _get_client(service: str, region: str = None):
    """Helper to create a boto3 client. Raises a clear error if creds are missing."""
    try:
        return boto3.client(service, region_name=region) if region else boto3.client(service)
    except NoCredentialsError:
        raise RuntimeError("AWS credentials not found. Check your .env file.")


# S3 tools

@tool
def list_s3_buckets() -> str:
    """
    List all S3 buckets in the AWS account with their region and public access status.
    Use this when the user asks about S3 buckets, storage, or wants to know what buckets exist.
    """
    try:
        s3 = _get_client("s3")
        buckets = s3.list_buckets().get("Buckets", [])

        if not buckets:
            return "No S3 buckets found in this AWS account."

        results = []
        for bucket in buckets:
            name = bucket["Name"]
            created = bucket["CreationDate"].strftime("%Y-%m-%d")

            # Check public access block settings
            try:
                pub = s3.get_public_access_block(Bucket=name)
                cfg = pub["PublicAccessBlockConfiguration"]
                is_public = not all([
                    cfg.get("BlockPublicAcls", False),
                    cfg.get("BlockPublicPolicy", False),
                    cfg.get("IgnorePublicAcls", False),
                    cfg.get("RestrictPublicBuckets", False),
                ])
                public_status = "⚠️  PUBLIC" if is_public else "🔒 Private"
            except ClientError:
                public_status = "❓ Unknown"

            results.append(f"• {name} | Created: {created} | {public_status}")

        return f"Found {len(buckets)} S3 bucket(s):\n" + "\n".join(results)

    except Exception as e:
        return f"Error listing S3 buckets: {str(e)}"


@tool
def check_s3_bucket_details(bucket_name: str) -> str:
    """
    Get detailed info about a specific S3 bucket: versioning, encryption, size estimate.
    Use when the user asks about a specific bucket by name.
    """
    try:
        s3 = _get_client("s3")
        details = [f"📦 Bucket: {bucket_name}"]

        # Versioning
        try:
            v = s3.get_bucket_versioning(Bucket=bucket_name)
            details.append(f"  Versioning: {v.get('Status', 'Disabled')}")
        except ClientError:
            details.append("  Versioning: Unable to fetch")

        # Encryption
        try:
            enc = s3.get_bucket_encryption(Bucket=bucket_name)
            rules = enc["ServerSideEncryptionConfiguration"]["Rules"]
            algo = rules[0]["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"]
            details.append(f"  Encryption: {algo}")
        except ClientError:
            details.append("  Encryption: None configured ⚠️")

        # Object count (first 1000)
        try:
            objs = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1000)
            count = objs.get("KeyCount", 0)
            truncated = " (1000+ objects, showing first 1000)" if objs.get("IsTruncated") else ""
            details.append(f"  Objects: {count}{truncated}")
        except ClientError:
            details.append("  Objects: Unable to list")

        return "\n".join(details)

    except Exception as e:
        return f"Error fetching bucket details: {str(e)}"


# IAM tools

@tool
def list_iam_roles() -> str:
    """
    List all IAM roles in the AWS account.
    Use when the user asks about IAM roles, permissions, or access controls.
    """
    try:
        iam = _get_client("iam")
        paginator = iam.get_paginator("list_roles")
        roles = []

        for page in paginator.paginate():
            roles.extend(page["Roles"])

        if not roles:
            return "No IAM roles found."

        lines = [f"Found {len(roles)} IAM role(s):"]
        for role in roles[:20]:  # cap at 20 to avoid token overflow
            lines.append(f"• {role['RoleName']} (created: {role['CreateDate'].strftime('%Y-%m-%d')})")

        if len(roles) > 20:
            lines.append(f"  ... and {len(roles) - 20} more roles.")

        return "\n".join(lines)

    except Exception as e:
        return f"Error listing IAM roles: {str(e)}"


@tool
def analyze_iam_role(role_name: str) -> str:
    """
    Analyse a specific IAM role's attached policies and flag any dangerous permissions
    like wildcard actions (*) or unrestricted resource access.
    Use when the user asks to audit, review, or check a specific IAM role.
    """
    try:
        iam = _get_client("iam")
        findings = [f"🔍 IAM Role Analysis: {role_name}"]
        warnings = []

        # Attached managed policies
        attached = iam.list_attached_role_policies(RoleName=role_name)["AttachedPolicies"]
        findings.append(f"\nAttached managed policies ({len(attached)}):")

        for policy in attached:
            findings.append(f"  • {policy['PolicyName']}")

            # Get the policy document
            try:
                policy_detail = iam.get_policy(PolicyArn=policy["PolicyArn"])
                version_id = policy_detail["Policy"]["DefaultVersionId"]
                doc = iam.get_policy_version(
                    PolicyArn=policy["PolicyArn"],
                    VersionId=version_id
                )["PolicyVersion"]["Document"]

                for stmt in doc.get("Statement", []):
                    actions = stmt.get("Action", [])
                    resources = stmt.get("Resource", [])
                    effect = stmt.get("Effect", "")

                    if isinstance(actions, str):
                        actions = [actions]
                    if isinstance(resources, str):
                        resources = [resources]

                    if effect == "Allow":
                        if "*" in actions or "iam:*" in actions:
                            warnings.append(
                                f"⚠️  {policy['PolicyName']}: Wildcard action (*) — overly permissive!"
                            )
                        if "*" in resources:
                            warnings.append(
                                f"⚠️  {policy['PolicyName']}: Wildcard resource (*) — applies to ALL resources!"
                            )
            except ClientError:
                findings.append(f"    (Could not read policy document)")

        # Inline policies
        inline = iam.list_role_policies(RoleName=role_name)["PolicyNames"]
        if inline:
            findings.append(f"\nInline policies ({len(inline)}): {', '.join(inline)}")

        # Summary
        if warnings:
            findings.append("\n🚨 Security findings:")
            findings.extend(warnings)
        else:
            findings.append("\n✅ No obvious wildcard permission issues found.")

        return "\n".join(findings)

    except iam.exceptions.NoSuchEntityException:
        return f"IAM role '{role_name}' not found."
    except Exception as e:
        return f"Error analysing IAM role: {str(e)}"


# EC2 tools

@tool
def list_ec2_instances(region: str = "us-east-1") -> str:
    """
    List all EC2 instances in a given region with their state, type, and tags.
    Use when the user asks about EC2 instances, servers, or compute resources.
    """
    try:
        ec2 = _get_client("ec2", region=region)
        response = ec2.describe_instances()

        instances = []
        for reservation in response["Reservations"]:
            instances.extend(reservation["Instances"])

        if not instances:
            return f"No EC2 instances found in {region}."

        lines = [f"Found {len(instances)} EC2 instance(s) in {region}:"]
        for inst in instances:
            name = next(
                (t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"),
                "Unnamed"
            )
            lines.append(
                f"• {name} | {inst['InstanceId']} | {inst['InstanceType']} | "
                f"State: {inst['State']['Name']}"
            )

        return "\n".join(lines)

    except Exception as e:
        return f"Error listing EC2 instances: {str(e)}"


# Export all tools for the agent to use
ALL_TOOLS = [
    list_s3_buckets,
    check_s3_bucket_details,
    list_iam_roles,
    analyze_iam_role,
    list_ec2_instances,
]


@tool
def parse_terraform_plan(plan_json: str) -> str:
    """
    Parse a Terraform plan JSON string and summarise what will be created,
    updated, or destroyed. Flags risky changes like IAM wildcard permissions,
    public S3 buckets, and open security groups.
    Usage: pass the output of 'terraform show -json <planfile>' as a string.
    """
    import json
    try:
        plan = json.loads(plan_json)
    except json.JSONDecodeError:
        return "❌ Invalid JSON. Run: terraform plan -out=plan.tfplan && terraform show -json plan.tfplan"

    changes = plan.get("resource_changes", [])
    if not changes:
        return "✅ No resource changes found in this plan."

    created, updated, destroyed, risks = [], [], [], []

    for r in changes:
        addr    = r.get("address", "unknown")
        actions = r.get("change", {}).get("actions", [])
        after   = r.get("change", {}).get("after") or {}

        if "create" in actions:
            created.append(addr)
        if "update" in actions:
            updated.append(addr)
        if "delete" in actions:
            destroyed.append(addr)

        # Risk checks
        rtype = r.get("type", "")
        if rtype in ("aws_iam_role_policy", "aws_iam_policy"):
            doc = str(after.get("policy", ""))
            if '"*"' in doc or "'*'" in doc:
                risks.append(f"🚨 {addr} — IAM policy contains wildcard (*) permissions")

        if rtype == "aws_s3_bucket_public_access_block":
            for field in ("block_public_acls", "block_public_policy",
                          "ignore_public_acls", "restrict_public_buckets"):
                if after.get(field) is False:
                    risks.append(f"⚠️  {addr} — {field} is set to false (public access risk)")

        if rtype == "aws_security_group_rule":
            cidr = after.get("cidr_blocks", [])
            if "0.0.0.0/0" in cidr:
                risks.append(f"⚠️  {addr} — Security group open to 0.0.0.0/0")

    lines = ["**Terraform Plan Summary**\n"]
    lines.append(f"➕ Create:  {len(created)} resource(s)")
    lines.append(f"✏️  Update:  {len(updated)} resource(s)")
    lines.append(f"🗑️  Destroy: {len(destroyed)} resource(s)\n")

    if created:
        lines.append("**Resources to create:**")
        lines += [f"  • {r}" for r in created]
    if updated:
        lines.append("\n**Resources to update:**")
        lines += [f"  • {r}" for r in updated]
    if destroyed:
        lines.append("\n**Resources to destroy:**")
        lines += [f"  • {r}" for r in destroyed]
    if risks:
        lines.append("\n**⚠️  Security Risks Detected:**")
        lines += [f"  {r}" for r in risks]
    else:
        lines.append("\n✅ No security risks detected in this plan.")

    return "\n".join(lines)


@tool
def fetch_cloudwatch_logs(log_group: str, lines: int = 20) -> str:
    """
    Fetch the most recent log lines from an AWS CloudWatch log group.
    Args:
        log_group: The CloudWatch log group name (e.g. /aws/lambda/my-function)
        lines: Number of recent log lines to return (default 20, max 100)
    """
    import boto3, time
    from botocore.exceptions import ClientError

    try:
        client = boto3.client("logs")
        lines  = min(int(lines), 100)

        # Get the most recent log stream
        streams = client.describe_log_streams(
            logGroupName=log_group,
            orderBy="LastEventTime",
            descending=True,
            limit=1
        ).get("logStreams", [])

        if not streams:
            return f"No log streams found in log group: {log_group}"

        stream_name = streams[0]["logStreamName"]
        end_time    = int(time.time() * 1000)
        start_time  = end_time - (6 * 3600 * 1000)  # last 6 hours

        events = client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            startTime=start_time,
            endTime=end_time,
            limit=lines,
            startFromHead=False
        ).get("events", [])

        if not events:
            return f"No recent log events in {log_group} / {stream_name}"

        result = [f"**CloudWatch Logs** — `{log_group}`",
                  f"Stream: `{stream_name}` | Last {len(events)} events\n"]
        for e in events:
            ts  = e.get("timestamp", 0) // 1000
            msg = e.get("message", "").strip()
            from datetime import datetime, timezone
            t = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%H:%M:%S")
            result.append(f"`{t}` {msg}")

        return "\n".join(result)

    except ClientError as e:
        return f"❌ AWS error: {e.response['Error']['Message']}"
    except Exception as e:
        return f"❌ Error: {str(e)}"
