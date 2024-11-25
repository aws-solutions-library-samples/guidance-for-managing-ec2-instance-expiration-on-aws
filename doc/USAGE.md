# Preface

This document describes how to use the guidance after it is deployed. See [DEPLOYMENT](DEPLOYMENT.md) for more details
on deploying the guidance.

# Overview

Once deployed, one need only set expiration tags on EC2 instances as desired.

# Expiration Tags

|                                         |                                                                             |
|-----------------------------------------|-----------------------------------------------------------------------------|
| **expiration:stop-after-duration**      | **Stop** the instance after a **duration** since its launch date/time.      |
| **expiration:stop-after-datetime**      | **Stop** the instance at an absolute **date/time**.                         |
| **expiration:terminate-after-duration** | **Terminate** the instance after a **duration** since its launch date/time. |
| **expiration:terminate-after-datetime** | **Terminate** the instance at an absolute **date/time**.                    |

> :memo: **Note:** The EC2 service defines an EC2 instance's "launch date/time" from the *last time* it was started -
> not from when it was created or started for the first time. (This behavior is not specific to this guidance.)
> A misunderstanding of this EC2 instance attribute can lead to unexpected behavior. For example, every time
> an instance with the **expiration:stop-after-duration** tag is started it becomes eligible once again to be stopped by
> the guidance.

## Duration Tag Format

`[#d][#h][#m][#s]`

The days, hours, minutes, and seconds fields are each optional and each prefixed with an integer.

Examples:

* 1d2h3m4s
* 10d14h
* 24h
* 10d

## Date/Time Tag Format

`YYYY-MM-DD HH:MM:SS UTC`

All fields (year, month, day, hours, minutes, seconds) are required and must be zero-padded to the length specified
by the format above. The `UTC` timezone designation is required (other timezones are not supported).

# Events

If the `EventBusName` CloudFormation template parameter value set during deployment refers to a valid Event Bus then
the guidance will emit events for actions taken (stopping or terminating EC2 instances). Also, an Event
Bus Rule will be created for these events. One may add targets to the rule, or use it as a reference for creating other
rules.

Example event:

```yaml
{
  "version": "0",
  "id": "6a7e8feb-b491-4cf7-a9f1-bf3703467718",
  "time": "2024-02-03T18:43:48Z",
  "account": "111122223333",
  "region": "us-east-1",
  "source": "InstanceExpiration",
  "detail-type": "Action",
  "detail":
  {
	"action": "STOP",
	"instance-id": "i-1234567890abcdef0",
  } 
}
```

# Notifications

If the `SnSTopicName` CloudFormation template parameter value set during deployment refers to a valid SNS Topic then
it will be added as a target to the Event Bus Rule, and any subscriptions to the SNS Topic will receive notifications
about expiration actions. For example, an administrator may subscribe their email address to the SNS Topic.

```
From:
    AWS Notifications <no-reply@sns.amazonaws.com>
	
Subject:
    AWS Notification Message
	
Body:
    "Action was taken on an expired EC2 instance."
		
    "When: 2024-07-02T21:43:57Z"
    "Account: 111122223333"
    "Region: us-east-1"
    "Stack: InstanceExpiration"
    "Action: STOP"
    "Instance: i-1234567890abcdef0"
```

# Scope

## Accounts

This guidance presently only acts within the AWS **account** in which it is deployed. No provisions are provided for use
across multiple accounts. One can deploy the guidance independently in multiple accounts.

## Regions

This guidance presently only acts within the AWS **region** in which it is deployed. No provisions are provided for use
across multiple regions. One can deploy the guidance independently in multiple regions (even within the same account).

# Risks

## Privilege Escalation

> :warning: **Warning:** With this guidance deployed and enabled it becomes possible to stop or terminate an EC2
> instance via editing its expiration tags. I.e., anybody (or anything) that can create or modify an expiration tag
> could abuse that permission to effectively stop or terminate the instance.

Note this is not a concern entirely unique to ths guidance. Tags are commonly, but not universally, used in access
control and automations. However, it is notable enough to warrant consideration.

### Case #1: Identities allowed to stop/terminate EC2 instances

Any IAM identity (IAM user or role) that are already allowed to stop/terminate EC2 instances cannot gain any advantage
via this guidance and are **not** a concern for privilege escalation.

### Case #2: Identities not allowed to create or edit EC2 instance tags

Any identities that cannot create or edit EC2 instance tags cannot gain any advantage via this guidance and are **not**
a concern for privilege escalation.

### Case #3: Identities allowed to create and edit EC2 instance tags but not otherwise stop/terminate EC2 instances

This is the case of concern for privilege escalation. With this guidance deployed and enabled such an identity could use
its ability to create or edit an EC2 instance's tag to cause the EC2 instance to be stopped or terminated.

The CloudFormation stack created by this guidance creates a Managed IAM Policy that denies creation and editing (and
deletion) of expiration tags. For environments where this risk is a concern, one can attach this policy to identities
as-desired to mitigate this risk. The Managed IAM Policy is **not** automatically attached - an administrator must take
this step after deploying the guidance. This policy can be found listed as one of the resources created by the stack and
also in the IAM service area of the AWS Management Console, and its default name starts with
`InstanceExpiration-DenyEc2ExpirationTagChanges`.

# Troubleshooting

Use the following as desired to look deeper into the guidance operation.

## Lambda Log

An AWS Lambda function runs in response to Amazon EventBridge Scheduler events and when EC2 instance `expiration:` tags
are modified. The log for the Lambda function is viewable within the Amazon CloudWatch service in the AWS Management
Console:

1. View the **Logs \ Log Groups** area of CloudWatch
2. Select the log group with name starting with **/aws/lambda/InstanceExpiration-Lambda**.