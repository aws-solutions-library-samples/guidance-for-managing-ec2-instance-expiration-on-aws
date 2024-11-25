"""
Project stack CloudFormation conditions container.
"""

# Copyright Amazon.com, Inc. and its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0



########################################################################################################################
# Imports
########################################################################################################################

import aws_cdk



########################################################################################################################
# Main Class
########################################################################################################################

class Conditions:
  """
  Creates conditions for the stack.
  """

  @property
  def EventBusNameNotEmpty(self):
    return self._event_bus_name_not_empty

  @property
  def SnsTopicNameNotEmpty(self):
    return self._sns_topic_name_not_empty

  @property
  def ActionRuleEnabled(self):
    return self._action_rule_enabled

  @property
  def ActionRuleSnsTargetEnabled(self):
    return self._action_rule_sns_target_enabled

  @property
  def CloudWatchEnabled(self):
    return self._cloudwatch_enabled



  def __init__(self, stack, params) -> None:

    self._event_bus_name_not_empty = aws_cdk.CfnCondition(stack, "CondEventBusNameNotEmpty",
      expression = aws_cdk.Fn.condition_not(
        aws_cdk.Fn.condition_equals(
          params.EventBusName,
          "",
        )
      )
    )

    self._sns_topic_name_not_empty = aws_cdk.CfnCondition(stack, "CondSnsTopicNameNotEmpty",
      expression = aws_cdk.Fn.condition_not(
        aws_cdk.Fn.condition_equals(
          params.SnsTopicName,
          "",
        )
      )
    )

    self._action_rule_enabled = aws_cdk.CfnCondition(stack, "CondActionRuleEnabled",
      expression = self._event_bus_name_not_empty.expression,
    )

    self._action_rule_sns_target_enabled = aws_cdk.CfnCondition(stack, "CondActionRuleSnsTargetEnabled",
      expression = aws_cdk.Fn.condition_and(
        self._action_rule_enabled.expression,
        self._sns_topic_name_not_empty.expression,
      )
    )

    self._cloudwatch_enabled = aws_cdk.CfnCondition(stack, "CondCloudWatchEnabled",
      expression = aws_cdk.Fn.condition_equals(
        params.CloudWatch,
        "Enable",
      )
    )
