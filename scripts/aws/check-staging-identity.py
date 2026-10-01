#!/usr/bin/env python3
"""Check an STS response without handling credentials or calling AWS."""
import json
import re
import sys

ACCOUNT = "005314670455"
ROLE = "family-life-os-staging-discovery"


def check_identity(identity):
    if not isinstance(identity, dict):
        raise ValueError("Expected an STS identity object.")
    if identity.get("Account") != ACCOUNT:
        raise ValueError("Refusing the wrong AWS account.")
    arn = identity.get("Arn", "")
    expected = rf"arn:aws:sts::{ACCOUNT}:assumed-role/{ROLE}/[A-Za-z0-9+=,.@_-]+"
    if not isinstance(arn, str) or not re.fullmatch(expected, arn):
        raise ValueError("Refusing an unexpected AWS principal or role.")
    return {
        "status": "identity_matches_expected_target",
        "account": ACCOUNT,
        "principal_arn": arn,
        "application_tests": "NOT_EXECUTED",
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: check-staging-identity.py <STS identity JSON file>")
    try:
        with open(sys.argv[1], encoding="utf-8") as source:
            result = check_identity(json.load(source))
    except (OSError, ValueError, TypeError) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(result, indent=2))