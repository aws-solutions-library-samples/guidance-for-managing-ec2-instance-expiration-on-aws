"""
Project stack Lambda policies container.
"""

# Copyright Amazon.com, Inc. and its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0



########################################################################################################################
# Imports
########################################################################################################################

import aws_cdk
from aws_cdk import (
  aws_iam,
)



########################################################################################################################
# Main Class
########################################################################################################################

class LambdaPolicies:
  """
  Creates Lambda policies for the stack.
  """

  def __init__(self, stack, params, conditions, ix_lambda_role,
    ix_next_schedule_arn_param, ix_next_schedule, ix_scheduler_role, ix_event_bus):

    #
    # Basic Policy
    #

    ix_lambda_policy = aws_iam.Policy(stack, "LambdaIamPolicy",
      statements = [
        aws_iam.PolicyStatement(
          actions = [
            "ec2:DescribeInstances",
          ],
          resources = ['*'],
        ),
        aws_iam.PolicyStatement(
          actions = [
            "ssm:GetParameter",
          ],
          resources = [ix_next_schedule_arn_param.parameter_arn],
        ),
        aws_iam.PolicyStatement(
          actions = [
            "scheduler:GetSchedule",
            "scheduler:UpdateSchedule",
          ],
          resources = [ix_next_schedule.schedule_arn],
        ),
        aws_iam.PolicyStatement(
          actions = [
            "iam:PassRole",
          ],
          resources = [ix_scheduler_role.role_arn],
        ),
      ]
    )

    # Stop and terminate EC2 instances (only EC2 instances with at least one expiration tag).
    expiration_tag_postfixes = [
      'stop-after-duration',
      'stop-after-datetime',
      'terminate-after-duration',
      'terminate-after-datetime',
    ]

    for postfix in expiration_tag_postfixes:
      ix_lambda_policy.add_statements(
        aws_iam.PolicyStatement(
          actions = [
            "ec2:StopInstances",
            "ec2:TerminateInstances",
          ],
          conditions = {
            "Null": aws_cdk.CfnJson(stack, "LambdaIamPolicy-" + postfix,
              value = {
                "ec2:ResourceTag/" + params.TagPrefix + ':' + postfix: "false",
              }
            )
          },
          resources = ['*'],
        )
      )

    # Attach the basics policy to the role.
    ix_lambda_role.attach_inline_policy(
      ix_lambda_policy
    )

    #
    # Events Policy
    #

    ix_lambda_policy_events = aws_iam.Policy(stack, "LambdaIamPolicyEvents",
      statements = [
        aws_iam.PolicyStatement(
          actions = [
            "events:PutEvents",
          ],
          conditions = {
            "StringEquals": {
              "events:source": stack.stack_name,
            }
          },
          resources = [ix_event_bus.event_bus_arn],
        ),
      ]
    )

    # Conditional on the EventBusName parameter.
    ix_lambda_policy_events.node.default_child.cfn_options.condition = conditions.EventBusNameNotEmpty

    # Attach the events policy to the role.
    ix_lambda_role.attach_inline_policy(
      ix_lambda_policy_events
    )
