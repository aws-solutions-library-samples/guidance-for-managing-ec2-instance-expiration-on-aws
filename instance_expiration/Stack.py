"""
Top-level stack for the 'Guidance for Instance Expiration on AWS' CDK app.
"""

# Copyright Amazon.com, Inc. and its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0



########################################################################################################################
# Imports
########################################################################################################################

import os
import datetime

import aws_cdk
from aws_cdk import (
  aws_events,
  aws_events_targets,
  aws_iam,
  aws_lambda,
  aws_lambda_event_sources,
  aws_logs,
  aws_sns,
  aws_sqs,
  aws_ssm,
  Duration,
  Stack,
)

try:
  from aws_cdk import (
    aws_scheduler_alpha,
    aws_scheduler_targets_alpha,
  )
except ImportError as err:
  print(err, '\n')
  print("This project requires AWS CDK alpha modules, which can be installed using the following command:\n")
  print("    pip install aws-cdk.aws-scheduler-alpha aws-cdk.aws-scheduler-targets-alpha --upgrade")
  exit()

import cdk_nag
from constructs import Construct
from instance_expiration.CloudWatch import CloudWatch
from instance_expiration.Parameters import Parameters
from instance_expiration.Conditions import Conditions
from instance_expiration.LambdaPolicies import LambdaPolicies
from instance_expiration.CdkConditionAspect import CdkConditionAspect



########################################################################################################################
# Main Class
########################################################################################################################

class Stack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:

    super().__init__(scope, construct_id, **kwargs)

    IX_SQS_MESSAGE_ID = "InstanceExpiration"
    IX_SSM_PARAM_NEXT_SCHEDULE_ARN = '/' + self.stack_name + '/NextScheduleArn'

    #
    # CloudFormation Template Parameters
    #

    params = Parameters(self)

    #
    # CloudFormation Template Conditions
    #

    conditions = Conditions(self, params)

    #
    # Lookup (do not create) existing resources referenced by parameters.
    #

    ix_event_bus = aws_events.EventBus.from_event_bus_name(self, "EventBus",
      event_bus_name = params.EventBusName,
    )

    ix_sns_topic = aws_sns.Topic.from_topic_arn(self, "SnsTopic",
      topic_arn = f"arn:aws:sns:{self.region}:{self.account}:{params.SnsTopicName}",
    )

    #
    # Instance Expiration Lambda: Checks for EC2 instances to stop/terminate and schedules its own next check.
    #

    # Lambda execution role (more policies are added way below after the necessary resources have been created).
    ix_lambda_role = aws_iam.Role(self, "LambdaIamRole",
      assumed_by = aws_iam.ServicePrincipal("lambda.amazonaws.com"),
      managed_policies = [
        aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
      ]
    )

    # Lambda function
    ix_lambda = aws_lambda.Function(self, "Lambda",
      architecture = aws_lambda.Architecture.ARM_64,
      runtime = aws_lambda.Runtime.PYTHON_3_12,
      code = aws_lambda.Code.from_asset(os.path.join("lambda", "InstanceExpiration")),
      handler = "Lambda.handler",
      role = ix_lambda_role,
      memory_size = 256,
      timeout = Duration.seconds(600),
      log_retention = aws_logs.RetentionDays.THREE_MONTHS,
      environment= {
        "CFN_STACK_NAME": self.stack_name,
        "IX_TAG_PREFIX": params.TagPrefix,
        "IX_STOP_ACTION": params.StopAction,
        "IX_TERM_ACTION": params.TermAction,
        "IX_EVENT_BUS_NAME": params.EventBusName,
        "IX_SSM_PARAM_NEXT_SCHEDULE_ARN": IX_SSM_PARAM_NEXT_SCHEDULE_ARN,
      }
    )

    #
    # Amazon Simple Queue Service (SQS) Queue: Events --> Queue --> Lambda
    #

    # Dead Letter Queue
    ix_dlq = aws_sqs.Queue(self, "DeadLetterQueue",
      fifo = True,                                      # Must be same type as primary queue
      enforce_ssl = True,
      content_based_deduplication = True,               # Required for FIFO queue
      retention_period = Duration.days(7)
    )

    # Queue
    ix_queue = aws_sqs.Queue(self, "Queue",
      fifo = True,                                      # FIFO required to use message group id for event serialization
      enforce_ssl = True,
      visibility_timeout = ix_lambda.timeout,
      content_based_deduplication = True,               # Required for FIFO queue
      dead_letter_queue = aws_sqs.DeadLetterQueue(
        queue = ix_dlq,
        max_receive_count = 3,
      )
    )

    # Queue --> Lambda
    ix_lambda.add_event_source(
      aws_lambda_event_sources.SqsEventSource(
        ix_queue,
        batch_size = 10,                                # Max number of events per Lambda invocation (max 10 for FIFO)
        #max_batching_window = Duration.seconds(5),     # Not allowed for FIFO queues
      )
    )

    #
    # Amazon EventBridge Schedulers: Used to schedule invocations of the Lambda.
    #

    # Scheduler role for invoking the target.
    ix_scheduler_role = aws_iam.Role(self, "SchedulerRole",
      assumed_by = aws_iam.ServicePrincipal(
        service = "scheduler.amazonaws.com",
        conditions = {
          "StringEquals": {
            "aws:SourceAccount": self.account,
          }
        }
      )
    )

    # Scheduler target = Queue
    ix_queue_target = aws_scheduler_targets_alpha.SqsSendMessage(
      queue = ix_queue,
      role = ix_scheduler_role,
      message_group_id = IX_SQS_MESSAGE_ID,             # Any unique value, for event serialization
    )

    # Schedule group (just to be tidy)
    ix_schedule_group = aws_scheduler_alpha.Group(self, "ScheduleGroup",
      group_name = self.stack_name,
      removal_policy = aws_cdk.RemovalPolicy.DESTROY,
    )

    # Schedule for the next asynchronous check; Lambda will subsequently schedule its own future checks.
    ix_next_schedule = aws_scheduler_alpha.Schedule(self, "NextSchedule",
      # NOTE: AWS CFN bug prevents retrieving ARN of scheduler in a group.
      #       (https://github.com/aws-cloudformation/cloudformation-coverage-roadmap/issues/1726)
      #group = ix_schedule_group,
      target = ix_queue_target,
      schedule = aws_scheduler_alpha.ScheduleExpression.at(
        # Required parameter, with no way to "leave it as it is" on a stack update. So set to shortly into the future
        # which, a) Has the nice effect of helping any other stack changes (ex: Lambda logic) take more immediate
        # effect, and, b) Is mostly harmless in any case. Worst case is we delayed the next action by a bit.
        datetime.datetime.now(tz = datetime.timezone.utc) + datetime.timedelta(minutes = 5)
      )
    )

    # Rate-based schedule as a backup to the primary checks (in case they fail to self-re-schedule).
    ix_rate_schedule = aws_scheduler_alpha.Schedule(self, "RateSchedule",
      # NOTE: AWS CFN bug prevents retrieving ARN of scheduler in a group.
      #       (https://github.com/aws-cloudformation/cloudformation-coverage-roadmap/issues/1726)
      #group = ix_schedule_group,
      target = ix_queue_target,
      schedule = aws_scheduler_alpha.ScheduleExpression.rate(
        Duration.minutes(params.BackupCheckPeriod)
      )
    )

    #
    # Amazon EventBridge Rule: Monitor for EC2 instance expiration tag changes
    #

    # Rule
    ix_tag_rule = aws_events.Rule(self, "TagRule",
      event_pattern = aws_events.EventPattern(
        source = [ "aws.tag" ],
        detail_type = [ "Tag Change on Resource" ],
        detail = {
          "service": [ "ec2" ],
          "resource-type": [ "instance" ],
          "changed-tag-keys": aws_events.Match.prefix(params.TagPrefix + ":"),
        },
      )
    )

    # Target
    ix_tag_rule.add_target(
      aws_events_targets.SqsQueue(
        queue = ix_queue,
        message_group_id = IX_SQS_MESSAGE_ID,           # Any unique value, for event serialization
        #message = None,                                # Accept default (entire EventBridge event)
      )
    )

    #
    # Amazon EventBridge Rule: Monitor for EC2 instance starts
    #

    # Rule
    ix_start_rule = aws_events.Rule(self, "StartRule",
      event_pattern = aws_events.EventPattern(
        source = [ "aws.ec2" ],
        detail_type = [ "EC2 Instance State-change Notification" ],
        detail = {
          "state": [ "running" ],
        },
      )
    )

    # Target
    ix_start_rule.add_target(
      aws_events_targets.SqsQueue(
        queue = ix_queue,
        message_group_id = IX_SQS_MESSAGE_ID,           # Any unique value, for event serialization
        #message = None,                                # Accept default (entire EventBridge event)
      )
    )

    #
    # Amazon EventBridge Rule: Subscribe to action events
    #

    # Target
    sns_target = aws_events_targets.SnsTopic(
      topic = ix_sns_topic,
      message = aws_events.RuleTargetInput.from_multiline_text(
        f"""Action was taken on an expired EC2 instance.

           When: {aws_events.EventField.from_path('$.time')}
           Account: {aws_events.EventField.from_path('$.account')}
           Region: {aws_events.EventField.from_path('$.region')}
           Stack: {aws_events.EventField.from_path('$.source')}
           Action: {aws_events.EventField.from_path('$.detail.action')}
           Instance: {aws_events.EventField.from_path('$.detail.instance-id')}"""
      )
    )

    # Rule
    ix_action_rule = aws_events.Rule(self, "ActionRule",
      event_bus = ix_event_bus,
      event_pattern = aws_events.EventPattern(
        source = [ self.stack_name ],
        detail_type = [ "Action" ],
      ),
      targets = [ sns_target ],
    )

    # Rule is conditional on ActionRuleEnabled
    ix_action_rule.node.default_child.cfn_options.condition = conditions.ActionRuleEnabled

    # Rule target is conditional on ActionRuleSnsTargetEnabled
    tgts_temp = ix_action_rule.node.default_child.targets
    ix_action_rule.node.default_child.targets = aws_cdk.Fn.condition_if(
      conditions.ActionRuleSnsTargetEnabled.logical_id,
      tgts_temp,
      aws_cdk.Aws.NO_VALUE
    )

    #
    # AWS SSM Parameters: For use by the Instance Expiration Lambda
    #

    # Next schedule ARN
    ix_next_schedule_arn_param = aws_ssm.StringParameter(self, "ParameterNextScheduleArn",
      parameter_name = IX_SSM_PARAM_NEXT_SCHEDULE_ARN,
      description = 'ARN of the AWS EventBridge Scheduler schedule that invokes the instance expiration lambda.',
      string_value = ix_next_schedule.schedule_arn,
    )

    #
    # Lambda IAM Policies
    #

    ix_lambda_policies = LambdaPolicies(self, params, conditions, ix_lambda_role,
      ix_next_schedule_arn_param, ix_next_schedule, ix_scheduler_role, ix_event_bus)

    #
    # IAM Policy: Deny expiration tag changes
    #
    # Not used by this stack, but made available should an admin want to attach it to roles/users to prevent them
    # from stopping/terminating EC2 instances via expiration tags.
    #

    ix_policy_deny_ec2_expiration_tag_changes = aws_iam.ManagedPolicy(self, "DenyEc2ExpirationTagChanges",
      statements = [
        aws_iam.PolicyStatement(
          effect = aws_iam.Effect.DENY,
          actions = [
            "ec2:CreateTags",
            "ec2:DeleteTags",
          ],
          conditions = {
            "ForAllValues:StringLike": {
              "aws:TagKeys": params.TagPrefix + ":*"
            },
          },
          #resources = "arn:aws:ec2:*:*:instance/*",
          resources = [
            aws_cdk.Arn.format(
              stack = self,
              components = aws_cdk.ArnComponents(
                service = "ec2",
                resource = "instance",
                resource_name = "*",
              )
            )
          ],
        ),
      ]
    )

    #
    # CloudWatch Dashboard
    #

    ix_cloudwatch = CloudWatch(self, "CloudWatchDashboard",
      ix_lambda = ix_lambda,
      ix_dlq = ix_dlq,
      ix_queue = ix_queue,
      ix_sched_group = "default",
      ix_tag_rule = ix_tag_rule,
      ix_start_rule = ix_start_rule,
    )

    # Conditionalize the entire dashboard on the related CFN template parameter.
    aws_cdk.Aspects.of(ix_cloudwatch).add(CdkConditionAspect(conditions.CloudWatchEnabled))

    #
    # cdk-nag Suppressions
    #

    cdk_nag.NagSuppressions.add_resource_suppressions(
      construct = ix_lambda_role,
      apply_to_children = True,
      suppressions = [
        {
          'id':
            'AwsSolutions-IAM4',
          'applies_to':
            ['Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'],
          'reason':
            'Using the standard managed policy for a Lambda function to execute.'
        },
      ],
    )

    cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
      stack = self,
      path = f"/{self.stack_name}/LambdaIamPolicy/Resource",
      apply_to_children = True,
      suppressions = [
        {
          'id':
            'AwsSolutions-IAM5',
          'applies_to':
            ['Resource::*'],
          'reason':
            'Project must be able to ec2:DescribeInstances to find EC2 instances with expiration '
            'tags to enforce, and the ec2:DescribeInstances action cannot be conditionalized.'
        },
      ],
    )

    cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
      stack = self,
      path = f"/{self.stack_name}/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole",
      apply_to_children = True,
      suppressions = [
        {
          'id':
            'AwsSolutions-IAM4',
          'applies_to':
            ['Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'],
          'reason':
            'AWS CDK creates a CustomResource to set CloudWatch log group retention policy, and uses the standard '
            'managed policy for its Lambda function to execute.'
        },
        {
          'id':
            'AwsSolutions-IAM5',
          'applies_to':
            ['Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'],
          'reason':
            'AWS CDK creates a CustomResource to set CloudWatch log group retention policy, and uses a resource '
            'wildcard in its Lambda function policy.'
        },
      ],
    )
