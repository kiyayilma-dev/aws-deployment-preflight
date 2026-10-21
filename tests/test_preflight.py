"""Unit tests for the AWS preflight checker."""

from unittest.mock import Mock

from botocore.exceptions import ClientError, NoCredentialsError

from src.preflight import PreflightChecker


def make_checker() -> PreflightChecker:
    """Create a checker without needing real AWS credentials."""
    checker = PreflightChecker.__new__(PreflightChecker)
    checker.region = "eu-north-1"
    checker.session = Mock()
    checker.config = Mock()
    return checker


def make_client_error(code: str) -> ClientError:
    """Build a realistic Botocore service error."""
    return ClientError(
        {
            "Error": {
                "Code": code,
                "Message": "Simulated error for unit testing",
            }
        },
        "TestOperation",
    )


def test_identity_passes_when_sts_returns_identity() -> None:
    checker = make_checker()
    sts = Mock()
    sts.get_caller_identity.return_value = {
        "Account": "123456789012",
        "Arn": "arn:aws:iam::123456789012:user/test-user",
        "UserId": "TESTUSER",
    }
    checker.session.client.return_value = sts

    result = checker.check_identity()

    assert result.status == "PASS"
    assert result.name == "AWS identity"
    assert "credentials are valid" in result.message


def test_identity_fails_when_credentials_are_missing() -> None:
    checker = make_checker()
    checker.session.client.side_effect = NoCredentialsError()

    result = checker.check_identity()

    assert result.status == "FAIL"
    assert "missing or incomplete" in result.message


def test_ec2_access_denied_is_a_warning() -> None:
    checker = make_checker()
    ec2 = Mock()
    ec2.describe_instances.side_effect = make_client_error(
        "UnauthorizedOperation"
    )
    checker.session.client.return_value = ec2

    result = checker.check_ec2_read_access()

    assert result.status == "WARN"
    assert "may not have permission" in result.message


def test_ec2_access_passes_when_request_succeeds() -> None:
    checker = make_checker()
    ec2 = Mock()
    ec2.describe_instances.return_value = {"Reservations": []}
    checker.session.client.return_value = ec2

    result = checker.check_ec2_read_access()

    assert result.status == "PASS"
    ec2.describe_instances.assert_called_once_with(MaxResults=5)


def test_s3_access_denied_is_a_warning() -> None:
    checker = make_checker()
    s3 = Mock()
    s3.list_buckets.side_effect = make_client_error("AccessDenied")
    checker.session.client.return_value = s3

    result = checker.check_s3_read_access()

    assert result.status == "WARN"
    assert "may be intentional" in result.message


def test_s3_access_passes_when_request_succeeds() -> None:
    checker = make_checker()
    s3 = Mock()
    s3.list_buckets.return_value = {"Buckets": []}
    checker.session.client.return_value = s3

    result = checker.check_s3_read_access()

    assert result.status == "PASS"
    s3.list_buckets.assert_called_once_with()
