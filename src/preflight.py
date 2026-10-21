"""Read-only AWS deployment preflight checks."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Literal

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
)

Status = Literal["PASS", "WARN", "FAIL"]


@dataclass
class CheckResult:
    """Represent one preflight check."""

    name: str
    status: Status
    message: str


class PreflightChecker:
    """Run read-only checks against an AWS account."""

    def __init__(self, region: str, profile: str | None = None) -> None:
        self.region = region
        self.session = boto3.Session(
            profile_name=profile,
            region_name=region,
        )
        self.config = Config(
            connect_timeout=5,
            read_timeout=10,
            retries={"max_attempts": 2, "mode": "standard"},
        )

    def check_identity(self) -> CheckResult:
        """Verify that the configured AWS identity can be resolved."""
        try:
            sts = self.session.client(
                "sts",
                region_name=self.region,
                config=self.config,
            )
            identity = sts.get_caller_identity()

            # Do not print the account ID or ARN in the report.
            if not identity.get("Arn") or not identity.get("Account"):
                return CheckResult(
                    "AWS identity",
                    "FAIL",
                    "AWS returned incomplete identity information.",
                )

            return CheckResult(
                "AWS identity",
                "PASS",
                "AWS credentials are valid and the identity was resolved.",
            )
        except (NoCredentialsError, PartialCredentialsError):
            return CheckResult(
                "AWS identity",
                "FAIL",
                "Credentials are missing or incomplete. Check your AWS CLI profile.",
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            if code in {
                "InvalidClientTokenId",
                "UnrecognizedClientException",
                "SignatureDoesNotMatch",
                "ExpiredToken",
                "InvalidAccessKeyId",
            }:
                return CheckResult(
                    "AWS identity",
                    "FAIL",
                    f"AWS rejected the configured credentials ({code}).",
                )

            if code in {"AccessDenied", "AccessDeniedException"}:
                return CheckResult(
                    "AWS identity",
                    "FAIL",
                    "The identity request was denied. Check the credential source and access restrictions.",
                )

            return CheckResult(
                "AWS identity",
                "FAIL",
                f"AWS could not verify the identity ({code}).",
            )
        except BotoCoreError as exc:
            # Avoid printing raw exception details that may contain endpoint or
            # environment information.
            return CheckResult(
                "AWS identity",
                "FAIL",
                f"Could not contact AWS or resolve credentials ({type(exc).__name__}).",
            )

    def check_ec2_read_access(self) -> CheckResult:
        """Check whether EC2 instance-description access is available."""
        try:
            ec2 = self.session.client(
                "ec2",
                region_name=self.region,
                config=self.config,
            )
            # Read-only API call. Do not print instance details.
            ec2.describe_instances(MaxResults=5)
            return CheckResult(
                "EC2 read access",
                "PASS",
                "The EC2 describe-instances request succeeded.",
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            if code in {"UnauthorizedOperation", "AccessDenied", "AccessDeniedException"}:
                return CheckResult(
                    "EC2 read access",
                    "WARN",
                    "The identity may not have permission to describe EC2 instances.",
                )
            return CheckResult(
                "EC2 read access",
                "WARN",
                f"The EC2 check could not be completed ({code}).",
            )
        except BotoCoreError as exc:
            return CheckResult(
                "EC2 read access",
                "WARN",
                f"The EC2 check could not reach AWS ({type(exc).__name__}).",
            )

    def check_s3_read_access(self) -> CheckResult:
        """Check whether account-level S3 bucket listing is permitted."""
        try:
            s3 = self.session.client(
                "s3",
                region_name=self.region,
                config=self.config,
            )
            # This checks ListAllMyBuckets permission. Bucket names are not
            # printed or retained.
            s3.list_buckets()
            return CheckResult(
                "S3 list access",
                "PASS",
                "The S3 bucket-listing request succeeded.",
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            if code in {"AccessDenied", "AccessDeniedException"}:
                return CheckResult(
                    "S3 list access",
                    "WARN",
                    "The identity cannot list all S3 buckets; this may be intentional.",
                )
            return CheckResult(
                "S3 list access",
                "WARN",
                f"The S3 check could not be completed ({code}).",
            )
        except BotoCoreError as exc:
            return CheckResult(
                "S3 list access",
                "WARN",
                f"The S3 check could not reach AWS ({type(exc).__name__}).",
            )


def available_regions() -> set[str]:
    """Return Regions known to the installed AWS SDK."""
    return set(boto3.session.Session().get_available_regions("ec2"))


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description="Run read-only AWS deployment preflight checks."
    )
    parser.add_argument(
        "--region",
        required=True,
        help="AWS Region, for example eu-north-1.",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Optional named AWS CLI profile.",
    )
    return parser.parse_args()


def print_report(results: list[CheckResult]) -> None:
    """Print a concise report without account identifiers."""
    print()
    print("AWS DEPLOYMENT PREFLIGHT")
    print("=" * 48)

    for result in results:
        print(f"[{result.status:<4}] {result.name}: {result.message}")

    critical_failure = any(
        result.status == "FAIL" for result in results
    )
    warning_present = any(
        result.status == "WARN" for result in results
    )

    print("-" * 48)
    if critical_failure:
        print("RESULT: FAIL — resolve critical checks before deployment.")
    elif warning_present:
        print("RESULT: REVIEW REQUIRED — some optional checks need attention.")
    else:
        print("RESULT: PASS — all configured checks succeeded.")

    print("No AWS resources were created, modified, or deleted.")
    print()


def main() -> int:
    """Run the preflight checks."""
    args = parse_args()

    if args.region not in available_regions():
        print(
            f"Invalid or unsupported AWS Region: {args.region}",
            file=sys.stderr,
        )
        print(
            "Use a Region supported by the installed AWS SDK.",
            file=sys.stderr,
        )
        return 2

    checker = PreflightChecker(args.region, args.profile)
    results = [
        checker.check_identity(),
        checker.check_ec2_read_access(),
        checker.check_s3_read_access(),
    ]

    print_report(results)

    # An identity failure is critical. Service-level access denials are
    # warnings because least-privilege AWS profiles may intentionally lack
    # access to one or both services.
    if results[0].status == "FAIL":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
