# Guidance for Instance Expiration on AWS

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Deployment](#deployment)
4. [Usage](#usage)
5. [Design](#design)
6. [Costs](#costs)
7. [Issues](#issues)
8. [Next Steps](doc/USAGE.md#events)
9. [Cleanup](doc/DEPLOYMENT.md#cleanup)
10. [Notices](#notices)

## Overview

Stops (or terminates) EC2 instances that have run (or existed) past the expiration values defined in their tags.

For example, the `expiration:stop-after-duration` tag could be used to stop the instance `1d2h` after its launch
date/time. Or, the `expiration:terminate-after-datetime` tag could be used to terminate the instance as of
`2024-03-15 12:00:00 UTC`.

Example use cases:

- Preset temporary EC2 instances to automatically terminate after a specified duration.
- Auto-stop an occasionally-used operations EC2 instance every time it is running for more than 1 day.
- Prevent ephemeral EC2 instances (ex: build agent machines) from existing beyond their expected use.
- Terminate an EC2 instance that has failed to continuously reset its own expiration tag 1 hour into the future.

> :warning: **Warning:** With this guidance deployed and enabled it becomes possible to stop or terminate an EC2
> instance via editing its expiration tags. I.e., anybody (or anything) that can create or modify an expiration tag
> could abuse that permission to effectively stop or terminate the instance. See [USAGE \ Risks](doc/USAGE.md#risks) for
> important considerations and mitigation.
 
## Features

**Relative and Absolute Tags** - The tag values can be relative to an EC2 instance's launch time (easier in some cases
because an automation does not need to calculate a future date) or an absolute date/time value.

**Event Driven** - The guidance monitors EC2 instance tags and schedules required stop/terminate actions using the
Amazon EventBridge Scheduler. This provides better precision (actions are very close to their schedule times) and
is more efficient than polling.

**Custom Tag Prefix** - The default `expiration:` tag prefix can be replaced with a custom value.

**Events** - Events for expiration actions are emitted to an Amazon EventBridge Event Bus for optional
integration/automation.

**Notifications** - If an SNS Topic is specified it will receive events for expiration actions, for example enabling
administrators to subscribe for notifications.

**CloudWatch Dashboard** - An optional CloudWatch Dashboard provides metrics, insights, and logs for the guidance.

## Deployment

The guidance is provided is an app based on the [AWS Cloud Development Kit (CDK)](https://aws.amazon.com/cdk/),
which is a free infrastructure-as-code platform. One runs the app to generate an
[AWS CloudFormation](https://aws.amazon.com/cloudformation/) template that is then deployed to an AWS account. This
results in a set of resources (Amazon EventBridge Scheduler, AWS Lambda, etc.) that implements the guidance.
Experience with the AWS CDK is **not** required.

See [DEPLOYMENT](doc/DEPLOYMENT.md) for more details on prerequisites and deploying the guidance.

## Usage

Once deployed, one need only set expiration tags on EC2 instances as desired.

See [USAGE](doc/USAGE.md) for more information on using the guidance.

## Design

Interested parties can read more about the design of this guidance in the [DESIGN](doc/DESIGN.md) documentation.

## Costs

This guidance is estimated to cost less than $1 USD / month to operate under even heavy usage, and less
than $10 USD / month under even the most extreme usage, excepting the optional CloudWatch Dashboard which adds
approximately $12 USD / month.

See [COSTS](doc/COSTS.md) for more information on costs.

## Issues

See the issue tracker within the repository site for known defects and features under consideration.

## Notices

See [LICENSE](LICENSE), [NOTICE](doc/NOTICE), and the following for important license, copyright, and disclaimer
information.

*Customers are responsible for making their own independent assessment of the information in this Guidance. This
Guidance: (a) is for informational purposes only, (b) represents AWS current product offerings and practices, which are
subject to change without notice, and (c) does not create any commitments or assurances from AWS and its affiliates,
suppliers or licensors. AWS products or services are provided “as is” without warranties, representations, or conditions
of any kind, whether express or implied. AWS responsibilities and liabilities to its customers are controlled by AWS
agreements, and this Guidance is not part of, nor does it modify, any agreement between AWS and its customers.*