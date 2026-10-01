# Staging provisioning prerequisites

The approved staging scope is EKS/ECR, PostgreSQL 16 with pgvector, TLS Redis,
private application S3, ClamAV, an internal ALB, CloudFront, API Gateway/VPC
Link, Secrets Manager and the required scoped IAM/controller/RBAC resources.
Keep the application's OTP/JWT. Do not introduce Cognito or deploy production.

The successful access check proved GitHub OIDC, the discovery identity, and a
bootstrap-stack metadata read in AWS. It did **not** grant provisioning access.
The discovery template explicitly denies non-metadata operations. Do not
replace that deny or attach AdministratorAccess to this role.

## Administrator action: gather metadata before creating resources

Run the following in AWS CloudShell using your existing authorized
administrator session. It needs Python 3 and AWS CLI v2, both normally supplied
by CloudShell. It does not request or print access keys, tokens, passwords or
secret values. Review the downloaded script before running it.

```bash
curl --fail --show-error --location \
  https://raw.githubusercontent.com/mdrvza/life-admin-ai/main/scripts/aws/collect-staging-inventory.py \
  --output /tmp/collect-staging-inventory.py

python3 /tmp/collect-staging-inventory.py \
  --output /tmp/family-life-os-staging-inventory.json
```

The script checks account `005314670455` before other API calls and requests
Mumbai (`ap-south-1`) metadata. It scans application/staging tags or known
staging name prefixes. Global S3/IAM/CloudFront metadata is filtered by the
same naming convention. Filters are **not** IAM security boundaries, and an
empty result does **not** prove that the account has no existing resources.
The script fails on denied/erroring API calls rather than inventing empty
results. The discovery role cannot run this broader inventory.

Download the resulting file using CloudShell's file-download action and share
it privately in this conversation. **Do not commit inventory output to the
public GitHub repository.** Mention any relevant untagged/differently named
existing resources, and whether any named staging roles already provide
provisioning access. Do not share credentials or secret values.

## What follows the inventory

1. Choose creation versus reuse using actual identifiers. Existing unrelated
   infrastructure and production remain untouched.
2. Prepare the missing network/compute/data foundation templates and a separate,
   administrator-reviewed execution bootstrap using these exact resource
   boundaries. IAM-bearing bootstrap remains administrator-controlled. Do not
   give GitHub an editable stack backed by a broad privileged execution role,
   unrestricted PassRole, or permissions to change its own IAM controls.
3. Establish a private-VPC execution path to the EKS API; GitHub OIDC by itself
   does not give a hosted runner network access to a private cluster endpoint.
4. Provision, install scoped/pinned controllers, deploy the actual application
   source and publish the frontend to the private staging bucket.
5. Run and preserve actual AWS staging test evidence. Report missing/failed
   prerequisites explicitly instead of marking tests verified.

## Real OTP prerequisites

The app already implements Twilio SMS delivery and conditional SMTP email
delivery; no Cognito or OTP bypass is needed. A functioning approved delivery
channel and isolated verified staging account are still required. Provider
credentials and test-account inputs must use protected secret flows, not
ConfigMaps, source control, inventory output or chat messages. The staging
ExternalSecret currently maps only JWT/encryption/database credentials; provider
configuration must be wired before claiming sign-in works.

Registration requires both email and SMS delivery. Clarify whether to reuse
existing configured providers or which real staging delivery channel is
approved before adding services or requesting provider secrets.

## Verification states

- GitHub OIDC/discovery identity/bootstrap stack metadata: already executed
  successfully in AWS.
- Foundation inventory: **NOT EXECUTED** until the administrator runs the script.
- Provisioning/application deployment: **NOT EXECUTED**.
- OTP/JWT, authenticated API, 25 MiB upload, ClamAV/S3, oversized rejection,
  frontend/backend connectivity and application health: **NOT EXECUTED**.
- Android AAB/Google Play Internal Testing: next phase, not started.