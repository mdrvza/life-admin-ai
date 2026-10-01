#!/usr/bin/env python3
"""Administrator-run metadata inventory. No AWS mutations or secret values."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess

ACCOUNT = "005314670455"
REGION = "ap-south-1"
READ_OPERATIONS = {
    ("sts", "get-caller-identity"),
    ("ec2", "describe-vpcs"),
    ("ec2", "describe-subnets"),
    ("ec2", "describe-security-groups"),
    ("eks", "list-clusters"),
    ("eks", "describe-cluster"),
    ("rds", "describe-db-instances"),
    ("elasticache", "describe-replication-groups"),
    ("ecr", "describe-repositories"),
    ("s3api", "list-buckets"),
    ("secretsmanager", "list-secrets"),
    ("elbv2", "describe-load-balancers"),
    ("apigatewayv2", "get-apis"),
    ("apigatewayv2", "get-vpc-links"),
    ("cloudfront", "list-distributions"),
    ("cloudformation", "list-stacks"),
    ("iam", "list-roles"),
}


def aws_metadata(service, operation, *arguments):
    if (service, operation) not in READ_OPERATIONS:
        raise ValueError("Refusing an operation outside the metadata-read allowlist.")
    command = [
        "aws", "--region", REGION, "--no-cli-pager",
        service, operation, *arguments, "--output", "json",
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    if result.returncode:
        match = re.search(r"An error occurred \(([A-Za-z0-9_.-]+)\)", result.stderr)
        code = match.group(1) if match else f"exit {result.returncode}"
        raise RuntimeError(f"{service} {operation} failed: {code}. No inventory was written.")
    try:
        return json.loads(result.stdout)
    except ValueError as error:
        raise RuntimeError(f"{service} {operation} did not return valid JSON.") from error


def collect_inventory(call=aws_metadata):
    identity = call("sts", "get-caller-identity")
    if not isinstance(identity, dict) or identity.get("Account") != ACCOUNT:
        raise ValueError("Refusing inventory outside the approved AWS account.")
    tag_filters = (
        "--filters",
        "Name=tag:Application,Values=family-life-os",
        "Name=tag:Environment,Values=staging",
    )
    resources = {}
    resources["vpcs"] = call(
        "ec2", "describe-vpcs", *tag_filters,
        "--query", "Vpcs[].{Id:VpcId,Cidr:CidrBlock,State:State}",
    )
    resources["subnets"] = call(
        "ec2", "describe-subnets", *tag_filters,
        "--query", "Subnets[].{Id:SubnetId,Vpc:VpcId,Cidr:CidrBlock,AZ:AvailabilityZone,PublicIpOnLaunch:MapPublicIpOnLaunch}",
    )
    resources["security_groups"] = call(
        "ec2", "describe-security-groups", *tag_filters,
        "--query", "SecurityGroups[].{Id:GroupId,Name:GroupName,Vpc:VpcId}",
    )
    resources["eks_cluster_names"] = call(
        "eks", "list-clusters", "--query",
        "clusters[?starts_with(@, 'family-life-os-staging')]",
    )
    if not isinstance(resources["eks_cluster_names"], list):
        raise RuntimeError("EKS cluster-name query did not return a list.")
    resources["eks_clusters"] = []
    for name in resources["eks_cluster_names"]:
        if not isinstance(name, str) or not re.fullmatch(r"family-life-os-staging[A-Za-z0-9_-]*", name):
            raise ValueError("Refusing an unexpected cluster name.")
        resources["eks_clusters"].append(call(
            "eks", "describe-cluster", "--name", name, "--query",
            "cluster.{Name:name,Arn:arn,State:status,Version:version,Endpoint:endpoint,RoleArn:roleArn,PrivateEndpoint:resourcesVpcConfig.endpointPrivateAccess,PublicEndpoint:resourcesVpcConfig.endpointPublicAccess,PublicAccessCidrs:resourcesVpcConfig.publicAccessCidrs,Vpc:resourcesVpcConfig.vpcId,Subnets:resourcesVpcConfig.subnetIds,ClusterSecurityGroup:resourcesVpcConfig.clusterSecurityGroupId,OidcIssuer:identity.oidc.issuer}",
        ))
    resources["postgres_instances"] = call(
        "rds", "describe-db-instances", "--query",
        "DBInstances[?starts_with(DBInstanceIdentifier, 'family-life-os-staging')].{Id:DBInstanceIdentifier,Arn:DBInstanceArn,State:DBInstanceStatus,Engine:Engine,Version:EngineVersion,Vpc:DBSubnetGroup.VpcId,Public:PubliclyAccessible,Encrypted:StorageEncrypted,Endpoint:Endpoint.Address,Groups:VpcSecurityGroups[].VpcSecurityGroupId,MasterSecretArn:MasterUserSecret.SecretArn}",
    )
    resources["redis_groups"] = call(
        "elasticache", "describe-replication-groups", "--query",
        "ReplicationGroups[?starts_with(ReplicationGroupId, 'family-life-os-staging')].{Id:ReplicationGroupId,Arn:ARN,State:Status,TransitEncrypted:TransitEncryptionEnabled,AtRestEncrypted:AtRestEncryptionEnabled,AuthEnabled:AuthTokenEnabled,Endpoints:NodeGroups[].PrimaryEndpoint}",
    )
    resources["ecr_repositories"] = call(
        "ecr", "describe-repositories", "--query",
        "repositories[?repositoryName=='family-life-os-backend' || starts_with(repositoryName, 'family-life-os-staging')].{Name:repositoryName,Arn:repositoryArn,Uri:repositoryUri,TagMutability:imageTagMutability,ScanOnPush:imageScanningConfiguration.scanOnPush}",
    )
    resources["s3_bucket_names"] = call(
        "s3api", "list-buckets", "--query",
        "Buckets[?starts_with(Name, 'family-life-os-staging')].Name",
    )
    resources["application_secret_metadata"] = call(
        "secretsmanager", "list-secrets", "--filters",
        "Key=name,Values=family-life-os/staging/",
        "--query", "SecretList[].{Name:Name,Arn:ARN,KmsKeyId:KmsKeyId}",
    )
    resources["load_balancers"] = call(
        "elbv2", "describe-load-balancers", "--query",
        "LoadBalancers[?starts_with(LoadBalancerName, 'family-life-os-staging')].{Name:LoadBalancerName,Arn:LoadBalancerArn,Scheme:Scheme,State:State.Code,Vpc:VpcId,Dns:DNSName,Groups:SecurityGroups,Subnets:AvailabilityZones[].SubnetId}",
    )
    resources["http_apis"] = call(
        "apigatewayv2", "get-apis", "--query",
        "Items[?starts_with(Name, 'family-life-os-staging')].{Name:Name,Id:ApiId,Protocol:ProtocolType,Endpoint:ApiEndpoint}",
    )
    resources["vpc_links"] = call(
        "apigatewayv2", "get-vpc-links", "--query",
        "Items[?starts_with(Name, 'family-life-os-staging')].{Name:Name,Id:VpcLinkId,State:VpcLinkStatus,Subnets:SubnetIds,Groups:SecurityGroupIds}",
    )
    resources["cloudfront_distributions"] = call(
        "cloudfront", "list-distributions", "--query",
        "DistributionList.Items[?contains(Comment, 'Family Life OS staging') || contains(Comment, 'family-life-os-staging')].{Id:Id,Arn:ARN,Domain:DomainName,State:Status,Enabled:Enabled}",
    )
    resources["staging_stacks"] = call(
        "cloudformation", "list-stacks", "--query",
        "StackSummaries[?starts_with(StackName, 'family-life-os-staging') && StackStatus!='DELETE_COMPLETE'].{Name:StackName,Id:StackId,State:StackStatus}",
    )
    resources["staging_roles"] = call(
        "iam", "list-roles", "--query",
        "Roles[?starts_with(RoleName, 'family-life-os-staging-')].{Name:RoleName,Arn:Arn}",
    )
    return {
        "account": ACCOUNT,
        "region": REGION,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Named/tagged staging candidates, not an exhaustive account audit.",
        "absence_is_not_proven": True,
        "untagged_or_differently_named_resources": "UNKNOWN",
        "application_tests": "NOT_EXECUTED",
        "resources": resources,
    }


def write_inventory(output, inventory):
    # Create exclusively; do not replace an existing report. Metadata can still
    # reveal infrastructure details, so restrict local permissions and sharing.
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as destination:
        json.dump(inventory, destination, indent=2)
        destination.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise SystemExit("Output already exists; choose a new filename.")
    try:
        inventory = collect_inventory()
        write_inventory(arguments.output, inventory)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error)) from error
    print(f"Read-only inventory saved to {arguments.output}.")
    print("No AWS resources changed. No application tests executed.")
    print("Keep this file private; do not commit it to the public GitHub repository.")


if __name__ == "__main__":
    main()