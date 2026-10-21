# AWS Deployment Preflight Checker



A Python CLI tool that checks selected AWS deployment prerequisites using Boto3. It validates AWS identity and tests read-only access to EC2 and S3 before deployment.



\## Features



\- Verify AWS identity using AWS STS.

\- Validate the requested AWS Region.

\- Check EC2 read access.

\- Check S3 bucket-listing access.

\- Report results using PASS, WARN, and FAIL statuses.

\- Run automated tests without requiring live AWS credentials.

\- Avoid creating, modifying, or deleting AWS resources.



\## Technology Stack



\- Python

\- Boto3

\- AWS STS, EC2, and S3

\- pytest

\- Git and GitHub



\## Requirements



\- Python 3.11 or newer

\- AWS CLI

\- Configured AWS credentials with the necessary read permissions



\## Installation



Clone the repository and enter its directory:



```powershell

git clone https://github.com/YOUR\_GITHUB\_USERNAME/aws-deployment-preflight.git

cd aws-deployment-preflight

```



Create and activate a virtual environment:



```powershell

py -m venv .venv

.\\.venv\\Scripts\\Activate.ps1

python -m pip install -r requirements.txt

```



\## Verify AWS Credentials



```powershell

aws sts get-caller-identity

```



\## Run the Checker



```powershell

python -m src.preflight --region eu-north-1

```



To use a named AWS CLI profile, replace `PROFILE\_NAME` with a real profile name:



```powershell

aws configure list-profiles

python -m src.preflight --region eu-north-1 --profile PROFILE\_NAME

```



\## Run Tests



```powershell

python -m pytest -v

```



\## Example Output



```text

AWS DEPLOYMENT PREFLIGHT

\[PASS] AWS identity: AWS credentials are valid and the identity was resolved.

\[PASS] EC2 read access: The EC2 describe-instances request succeeded.

\[PASS] S3 list access: The S3 bucket-listing request succeeded.

RESULT: PASS â€” all configured checks succeeded.

No AWS resources were created, modified, or deleted.

```



Actual results depend on AWS permissions, credentials, network connectivity, and the selected Region.



\## Safety



This tool performs read-only AWS checks. It does not deploy infrastructure or create, modify, or delete AWS resources.



A successful preflight does not guarantee that every deployment requirement has been satisfied.



\## Project Structure



```text

aws-deployment-preflight/

â”œâ”€â”€ src/

â”‚   â”œâ”€â”€ \_\_init\_\_.py

â”‚   â””â”€â”€ preflight.py

â”œâ”€â”€ tests/

â”‚   â”œâ”€â”€ \_\_init\_\_.py

â”‚   â””â”€â”€ test\_preflight.py

â”œâ”€â”€ .gitignore

â”œâ”€â”€ pytest.ini

â”œâ”€â”€ requirements.txt

â””â”€â”€ README.md

```



\## Future Improvements



\- Add configurable service checks.

\- Improve diagnostics for common AWS errors.

\- Add GitHub Actions continuous integration.

\- Add structured JSON output for automation.




