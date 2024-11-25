# Preface

This document describes the design of the guidance, which is not necessary to deploy (see [DEPLOYMENT](DEPLOYMENT.md))
or use (see [USAGE](USAGE.md)) the guidance.

# Diagram

[<img src="instance-expiration-design.png">](instance-expiration-design.png)

# Lambda Function

The core of the guidance is an AWS Lambda function, which upon invocation:

1. Scans EC2 instances (metadata only).
   * Filtering to only instances with at least one expiration tag.
2. Sorts EC2 instance list by next expiration action date/time.
   * Soonest first.
3. Handles expired instances.
   * Those with an expiration action date/time <= now.
   * Stopping or terminating, as appropriate.
4. Schedules the next invocation.
   * Based on the first instance in the sorted list with expiration action date/time > now.

Note that there is **not** a schedule for each EC2 instance with an expiration tag. There is only ever a single schedule
for the **next** EC2 instance expiration tag date/time.

# Lambda Function Triggers

The AWS Lambda Function is triggered by messages from an Amazon SQS Queue.

The sources of queue messages are:

1. EC2 instance lifecycle start notifications.
   * Instance state --> running.
2. EC2 instance tag change notifications.
   * Filtered to the expiration tag prefix.
   * Also accounts for creation of new EC2 instances.
3. Next Lambda invocation schedule.
   * As set by the Lambda.
4. Backup check schedule.
   * See below.

Through the above, the Lambda always takes appropriate actions (stopping and terminating instances) in a timely manner
and keeps its next scheduled invocation correct.

Note it is not necessary to trigger the Lambda on EC2 instance stop or termination - the Lambda executing and finding
no action to take is not problematic. And from a cost perspective, this case of an unnecessary Lambda execution is
thought to be less frequent than triggering the Lambda for EC2 instance stops and terminations when the instance with
the state change was not the one related to the next scheduled invocation.

# Backup Check Schedule

In addition to the pure event driven design of this guidance, there is a periodic schedule set by the
`BackupCheckPeriod` parameter. When this schedule triggers, it sends a message to the queue and thus invokes the Lambda
function. In theory, this invocation will not result in an action except if/when:

* The timing of the periodic event is immediately before an actual expiration tag expiration by the time the
Lambda executes.

* The Lambda previously missed or failed to succeed in its action for an expired tag.

The purpose of the backup check schedule is the latter, so that a missed tag expiration may be
eventually caught/fixed instead of the EC2 instance running (or existing) in perpetuity.  I.e., "better late than never"

Although expected to be rare, example missed or failed cases are:

* AWS service outage prevented the guidance from completing an intended action (ex: EC2 API to stop an instance was
unavailable for an extended period of time).

* Manual intervention or misconfiguration broke the guidance temporarily (ex: lacked sufficient permission to
stop an EC2 instance).

Note that unless there are a tremendous number of EC2 instances (with the expiration tag) for the Lambda to process (and
thus the Lambda executes for an extended period of time), the cost for these backup check invocations will be
negligible.

# Lambda Function Verifier

As an additional safeguard against unintended behavior, at the point in the Lambda code where it would execute an
action there is logic to double-check by independently inspecting the targeted EC2 instance metadata versus the
upcoming action and requirements - the EC2 instance must have a matching expiration tag that is expired and the EC2
guidance deployment parameter for the action must be enabled.

Note this verification check does not make the guidance infallible, but in theory it could catch defects that may have
otherwise resulted in an unintended action.

# Message Queue

The Lambda function could be invoked directly from the Amazon EventBridge events. The use of a queue:

* Persists the messages through an intermittent Lambda failure or AWS Lambda service outage.

* Allows the Lambda to service messages in batches, for efficiency (however unlikely it is that the event rate
exceeds the Lambda service rate).