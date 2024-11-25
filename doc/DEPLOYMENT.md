# Preface

This document describes how to deploy the guidance, which is done one time before using it in perpetuity. See
[USAGE](USAGE.md) for more information on using the deployed guidance.

# Overview

The guidance is provided is an app based on the [AWS Cloud Development Kit (CDK)](https://aws.amazon.com/cdk/),
which is a free infrastructure-as-code platform. One runs the app to generate an [AWS CloudFormation](https://aws.amazon.com/cloudformation/)
template that is then deployed to an AWS account. This results in a set of resources (Amazon EventBridge Scheduler, AWS
Lambda, etc.) that implements the guidance. Experience with the AWS CDK is *not* required to deploy and use the
guidance.

# Deployment

## Prerequisite: AWS Cloud Development Kit

Python and the AWS CDK are required to build the guidance. Choose one of the following paths.

### 1) Use the AWS CloudShell

The [AWS CloudShell](https://aws.amazon.com/cloudshell/) has all the prerequisites for building and deploying AWS CDK
apps like this guidance and is available with one-click in the AWS Management Console. This makes it fast
and easy to deploy the guidance. See
[How to get started with the AWS CloudShell](https://docs.aws.amazon.com/cloudshell/latest/userguide/welcome.html#how-to-get-started)
for screenshots of how to open the AWS CloudShell.

### 2) Use an Existing AWS CDK Setup

Optionally review
[AWS Cloud Development Kit (CDK) Guide \ Getting Started](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)
to confirm your existing AWS CDK environment.

### 3) Create a New AWS CDK Setup

See [AWS Cloud Development Kit (CDK) Guide \ Getting Started](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) for instructions.

The typical general steps:

1. Install Node.js
2. Install Python
3. Install and setup the AWS CLI
4. Install AWS CDK
 
## CDK Version

Your AWS CDK command line interface (CLI) must be sufficiently up-to-date. Especially if using the AWS CloudShell,
execute the following command to update your AWS CDK CLI:

Windows:
```
npm install -g aws-cdk
```

Linux (including AWS CloudShell):
```
sudo npm install -g aws-cdk
```

## CDK Bootstrap

In all cases and as with any AWS CDK app, the AWS account in which to deploy the guidance must be bootstrapped for use
with the AWS CDK. If your account has never been bootstrapped, execute the following command (note that duplicate
bootstrapping of an account is safe):

```
cdk bootstrap aws://ACCOUNT-ID/REGION-ID
```

Your ACCOUNT-ID is a 12-digit number and can be
[found in the account drop-down in the upper-right of the AWS Management Console](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-identifiers.html#FindAccountId)
or by executing this command:

```
aws sts get-caller-identity
```

Your REGION-ID can be
[found in the region drop-down in the upper right of the AWS Management Console](https://docs.aws.amazon.com/awsconsolehelpdocs/latest/gsg/select-region.html)
or by inspecting an AWS CloudShell environment variable:

```
echo $AWS_REGION
```

Here is an example bootstrap command:

```
cdk bootstrap aws://123456789012/us-east-1
```

## Clone the Repository

Use a Git client to clone the repo:

```
git clone https://github.com/aws-solutions-library-samples/guidance-for-instance-expiration-on-aws.git
```

Alternatively, download the repo contents manually to a local folder:

* https://github.com/aws-solutions-library-samples/guidance-for-instance-expiration-on-aws

## Build the App

Optionally create and activate a [Python virtual environment](https://docs.python.org/3/library/venv.html) for the
project to isolate it from the machine's general Python environment:

```
cd guidance-for-instance-expiration-on-aws
python -m venv .venv
source .venv/bin/activate
```

Install the app's Python dependencies:

```
pip install -r requirements.txt
```

Use the typical CDK command to build and deploy the app.

```
cdk deploy
```

Several CloudFormation parameters can be supplied on the deploy command line:

| Name              | Values             | Default    | Purpose                                                     |
|-------------------|--------------------|------------|-------------------------------------------------------------|
| TagPrefix         | String             | expiration | Prefix for the EC2 instance tags inspected.                 |
| StopAction        | Enable \| Disable  | Enable     | Enable or disable stopping EC2 instances.                   |
| TerminateAction   | Enable \| Disable  | Enable     | Enable or disable terminating EC2 instances.                |
| BackupCheckPeriod | Integer (minutes)  | 60         | Period for backup expiration check invocations, in minutes. |
| EventBusName      | String             | default    | Name of existing EventBridge bus for action events.         |
| SnsTopicName      | String             |            | Name of existing SNS Topic for action event notifications.  |
| CloudWatch        | Enable \| Disable  | Disable    | Enable or disable CloudWatch dashboard.                     |

Note that `SnsTopicName` only takes effect if `EventBusName` is not empty because notifications via an SNS Topic
depend upon action events via an Event Bus.

Example command line to deploy the app with some parameter values specified:

```
cdk deploy \
  --parameters TagPrefix=acme:it:expiration \
  --parameters SnsTopicName=ops-alerts
```

## Inspect Deployment

Like all AWS CDK deployed apps, the result is an AWS CloudFormation stack.

One can view the resulting stack within the AWS CloudFormation service in the AWS Management Console, including its
resources and outputs. The default stack name is **InstanceExpiration**.

# Cleanup

Use the following CDK command to remove the deployed guidance:

```
cdk destroy
```