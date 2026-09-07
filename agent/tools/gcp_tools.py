"""
InfraBot — GCP tools
Requires: GOOGLE_APPLICATION_CREDENTIALS set in .env pointing to a service account JSON
or running on a GCP machine with ADC (Application Default Credentials).
"""
from langchain_core.tools import tool


@tool
def list_gcs_buckets() -> str:
    """
    List all Google Cloud Storage (GCS) buckets in the configured GCP project.
    Returns bucket names, locations, storage class, and public access status.
    """
    try:
        from google.cloud import storage
        client = storage.Client()
        buckets = list(client.list_buckets())

        if not buckets:
            return "No GCS buckets found in this GCP project."

        lines = [f"**GCS Buckets** ({len(buckets)} found)\n"]
        for bucket in buckets:
            bucket.reload()
            iam_config = bucket.iam_configuration
            public = not iam_config.uniform_bucket_level_access_enabled
            status = "🚨 PUBLIC ACCESS POSSIBLE" if public else "🔒 Uniform access enabled"
            lines.append(
                f"• **{bucket.name}**\n"
                f"  Location: {bucket.location} | Class: {bucket.storage_class}\n"
                f"  Access: {status}"
            )
        return "\n".join(lines)

    except ImportError:
        return "❌ google-cloud-storage not installed. Run: pip3 install google-cloud-storage"
    except Exception as e:
        return f"❌ GCP error: {str(e)}\nMake sure GOOGLE_APPLICATION_CREDENTIALS is set in .env"


@tool
def list_gcp_iam_bindings(project_id: str = "") -> str:
    """
    List IAM policy bindings for a GCP project — who has what role.
    Args:
        project_id: GCP project ID. Leave blank to use the default from credentials.
    """
    try:
        from google.cloud import resourcemanager_v3

        client = resourcemanager_v3.ProjectsClient()

        if not project_id:
            import google.auth
            _, project_id = google.auth.default()

        if not project_id:
            return "❌ No project ID found. Pass it explicitly or set GOOGLE_CLOUD_PROJECT in .env"

        resource = f"projects/{project_id}"
        policy = client.get_iam_policy(resource=resource)

        if not policy.bindings:
            return f"No IAM bindings found for project: {project_id}"

        lines = [f"**GCP IAM Bindings** — project: `{project_id}`\n"]
        risks = []

        for binding in policy.bindings:
            role = binding.role
            members = list(binding.members)
            lines.append(f"**{role}**")
            for m in members:
                lines.append(f"  • {m}")
                if "allUsers" in m or "allAuthenticatedUsers" in m:
                    risks.append(
                        f"🚨 {role} granted to {m} — publicly accessible!")
            lines.append("")

        if risks:
            lines.append("**⚠️ Security Risks:**")
            lines += risks

        return "\n".join(lines)

    except ImportError:
        return "❌ google-cloud-resource-manager not installed. Run: pip3 install google-cloud-resource-manager"
    except Exception as e:
        return f"❌ GCP error: {str(e)}"


@tool
def multi_cloud_audit() -> str:
    """
    Run a full security audit across both AWS and GCP.
    Checks S3 buckets, IAM roles (AWS), GCS buckets, and GCP IAM bindings.
    Returns a consolidated multi-cloud security report.
    """
    import boto3
    from botocore.exceptions import ClientError

    report = ["# 🔍 Multi-Cloud Security Audit\n"]
    report.append("=" * 50)

    # ── AWS S3 ────────────────────────────────────────────────────────────────
    report.append("\n## ☁️  AWS — S3 Buckets")
    try:
        s3 = boto3.client("s3")
        buckets = s3.list_buckets().get("Buckets", [])
        aws_risks = []
        for b in buckets:
            name = b["Name"]
            try:
                r = s3.get_public_access_block(Bucket=name)
                cfg = r["PublicAccessBlockConfiguration"]
                if not all(cfg.values()):
                    aws_risks.append(
                        f"🚨 {name} — public access not fully blocked")
                    report.append(f"  🚨 {name} — PUBLIC")
                else:
                    report.append(f"  ✅ {name} — private")
            except ClientError:
                report.append(
                    f"  ⚠️  {name} — could not check access settings")
        if not aws_risks:
            report.append("  ✅ All S3 buckets have public access blocked.")
    except Exception as e:
        report.append(f"  ❌ Could not check S3: {str(e)}")

    # ── AWS IAM ───────────────────────────────────────────────────────────────
    report.append("\n## 🔐 AWS — IAM Roles")
    try:
        iam = boto3.client("iam")
        roles = iam.list_roles(MaxItems=20).get("Roles", [])
        report.append(f"  Found {len(roles)} roles (showing up to 20)")
        wildcard_count = 0
        for role in roles:
            rname = role["RoleName"]
            try:
                policies = iam.list_attached_role_policies(
                    RoleName=rname).get("AttachedPolicies", [])
                for pol in policies:
                    pv = iam.get_policy(PolicyArn=pol["PolicyArn"])
                    ver = pv["Policy"]["DefaultVersionId"]
                    doc = str(iam.get_policy_version(
                        PolicyArn=pol["PolicyArn"], VersionId=ver))
                    if '"*"' in doc:
                        wildcard_count += 1
                        report.append(
                            f"  🚨 {rname} — wildcard (*) permissions via {pol['PolicyName']}")
            except Exception:
                pass
        if wildcard_count == 0:
            report.append("  ✅ No wildcard IAM permissions detected.")
    except Exception as e:
        report.append(f"  ❌ Could not check IAM: {str(e)}")

    # ── GCP ───────────────────────────────────────────────────────────────────
    report.append("\n## 🌐 GCP — Cloud Storage")
    try:
        from google.cloud import storage
        gcs = storage.Client()
        buckets = list(gcs.list_buckets())
        for bucket in buckets:
            bucket.reload()
            public = not bucket.iam_configuration.uniform_bucket_level_access_enabled
            icon = "🚨" if public else "✅"
            report.append(f"  {icon} {bucket.name}")
        if not buckets:
            report.append("  No GCS buckets found.")
    except Exception as e:
        report.append(f"  ⚠️  GCP not configured: {str(e)}")

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    report.append("\n" + "=" * 50)
    report.append("## 📋 Audit Complete")
    report.append("Review 🚨 items above for immediate action.")

    return "\n".join(report)


ALL_GCP_TOOLS = [list_gcs_buckets, list_gcp_iam_bindings, multi_cloud_audit]
