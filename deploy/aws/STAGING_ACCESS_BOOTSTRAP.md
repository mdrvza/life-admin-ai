# Administrator bootstrap — AWS staging access

This is an access bootstrap, **not an application deployment**. It does not
create EKS, databases, Redis, buckets, an ALB, or an edge distribution. Existing
OTP/JWT application authentication remains unchanged. No Cognito is involved.

## Approved target

- AWS account: `005314670455`
- AWS region: `ap-south-1` (Mumbai)
- GitHub repository: `mdrvza/life-admin-ai`
- Protected GitHub environment: `staging`
- Role: `family-life-os-staging-discovery`
- CloudFormation stack: `family-life-os-staging-access-bootstrap`

GitHub's authenticated repository/OIDC API reported this immutable subject:

```text
repo:mdrvza@308700480/life-admin-ai@1399300021:environment:staging
```

The name-only subject is **not** correct for this repository. If the repository
is transferred, renamed, recreated or its OIDC customization changes, recheck
the real subject and review the trust policy. Do not widen it with wildcards.

## Why this first role is deliberately read-only

There is no existing staging provisioning role, and actual AWS resource IDs are
unknown. Granting GitHub broad IAM mutation or an editable CloudFormation stack
with a privileged execution role would create an escalation path.

The bootstrap role can only read named staging CloudFormation stack metadata,
describe the named staging EKS cluster, and describe (not retrieve) the one
staging application secret. It cannot provision anything, read S3 objects,
retrieve secrets, assume another role, pass roles, change IAM, administer EKS
access, or deploy production. There is no account-wide inventory permission.
Its explicit deny makes attaching a deployment policy to this discovery role
ineffective; use a separate reviewed execution role later.

Network/data/edge resources outside the named stacks remain **UNKNOWN**, not
absent. The administrator must supply their staging identifiers or sanitized
metadata. After this inventory, prepare resource-specific execution access and
the missing foundation templates for administrator review. Bootstrap success
alone does **not** unblock application provisioning.

## One-time AWS administrator actions

Use an existing authorized administrator session, not root credentials and not
credentials copied into Replit or GitHub.

1. Confirm the account with `aws sts get-caller-identity`. Stop unless `Account`
   is exactly `005314670455`. Select region `ap-south-1`.
2. In IAM **Identity providers**, check for
   `https://token.actions.githubusercontent.com`. If present, confirm its
   audience contains `sts.amazonaws.com`; do not overwrite a shared provider.
3. In the Mumbai CloudFormation console, create a stack using
   `deploy/aws/iam/staging-access-bootstrap.yaml`. Name it
   `family-life-os-staging-access-bootstrap`.
4. Set `CreateGitHubOidcProvider=false` when the provider already exists, or
   `true` only when it is absent. A new provider is retained on stack deletion,
   because it may later be shared; remove it only after reviewing its consumers.
5. Review the change set: it may create only the discovery role and, if chosen,
   the GitHub OIDC provider. Acknowledge named IAM resources and execute it.
   Wait for `CREATE_COMPLETE` (or `UPDATE_COMPLETE`).
6. Confirm the role ARN output is
   `arn:aws:iam::005314670455:role/family-life-os-staging-discovery`, and the
   provisioning-permissions output is `NONE`. Report the non-secret stack
   status and role ARN. Do not send session keys or secret values.

The template includes account/region assertions. Still perform the identity
check before applying it; local validation is not proof of its AWS execution.

## GitHub administrator actions

1. Add the reviewed bootstrap files and
   `.github/workflows/aws-staging-access-check.yml` to the repository's `main`
   branch. The workflow expects `scripts/aws/check-staging-identity.py` at the
   repository root; do not nest this bootstrap under `lifeadmin_final/`.
   When using the uploaded bootstrap package, the inactive workflow sample is
   at `deploy/aws/bootstrap-workflow/aws-staging-access-check.yml`. A GitHub
   administrator must copy it to `.github/workflows/aws-staging-access-check.yml`
   to activate it; the current connector has no OAuth `workflow` scope.
2. Protect the `staging` environment with an administrator reviewer and restrict
   deployments to `main`. Prevent self-review when a second administrator is
   available. In a single-administrator setup, approving one's own
   **read-only access check** is permitted; re-review this choice before adding
   resource-mutating workflows. Disable administrator bypass where supported.
3. The OIDC environment subject itself does not enforce a branch restriction.
   Do not rely on the workflow's `if` alone; keep the environment restriction.
4. After the AWS stack completes, manually run **AWS staging access check
   (no deployment)** from `main`, and approve its environment gate.
5. Preserve the Actions run URL and logs. A successful run proves only an
   actual AWS STS exchange for the expected account and role, plus a named
   bootstrap-stack metadata read. None of the application flows is verified.

No AWS keys need to be added as GitHub or Replit secrets. The action requests a
15-minute session. It does not print its temporary credentials or OIDC token.

## Remaining gates before the first application test

- Identify existing approved staging resources; report denied/unknown checks
  rather than claiming resources are absent.
- Prepare/review the missing VPC/EKS/RDS/Redis foundation and specific execution
  permissions. IAM-bearing stacks stay administrator-controlled.
- Establish a runner path to the private EKS API; GitHub-hosted runners do not
  gain private-VPC access merely by assuming an AWS role.
- Generate staging application secrets securely in AWS, and configure the real
  OTP delivery/test-recipient path. Do not enable a fake OTP bypass.
- Follow `README.md` for application/edge deployment, then execute the seven
  requested AWS flows and retain actual logs/results.

**Current application test state: NOT EXECUTED.**

## Local checks (no AWS calls)

```bash
cfn-lint --region ap-south-1 -t deploy/aws/iam/staging-access-bootstrap.yaml
python3 scripts/validation/aws_staging_access_check.py
```

Local checks prove only template structure and fail-closed identity handling.
They do not prove federation or application behavior in AWS.

## References

- https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws
- https://docs.github.com/en/actions/reference/security/oidc#immutable-subject-claims
- https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-iam-oidcprovider.html