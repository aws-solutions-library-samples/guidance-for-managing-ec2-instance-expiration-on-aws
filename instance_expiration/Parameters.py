"""
Project stack CloudFormation parameters container.
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

class Parameters:
  """
  Creates parameters for the stack.
  """

  @property
  def TagPrefix(self):
    return self._tag_prefix.value_as_string

  @property
  def StopAction(self):
    return self._stop_action.value_as_string

  @property
  def TermAction(self):
    return self._term_action.value_as_string

  @property
  def BackupCheckPeriod(self):
    return self._backup_check_period.value_as_number

  @property
  def EventBusName(self):
    return self._event_bus_name.value_as_string

  @property
  def SnsTopicName(self):
    return self._sns_topic_name.value_as_string

  @property
  def CloudWatch(self):
    return self._cloudwatch.value_as_string



  def __init__(self, stack) -> None:

    self._tag_prefix = aws_cdk.CfnParameter(stack, "TagPrefix",
      type = "String",
      default = "expiration",
      description = "Prefix for the EC2 instance tags inspected by this project."
    )

    self._stop_action = aws_cdk.CfnParameter(stack, "StopAction",
      type = "String",
      default = "Enable",
      allowed_values = ["Enable", "Disable"],
      description = "Enable or disable stopping EC2 instances."
      )

    self._term_action = aws_cdk.CfnParameter(stack, "TerminateAction",
      type = "String",
      default = "Enable",
      allowed_values = ["Enable", "Disable"],
      description = "Enable or disable terminating EC2 instances."
      )

    self._backup_check_period = aws_cdk.CfnParameter(stack, "BackupCheckPeriod",
      type = "Number",
      default = "60",
      min_value = 1,
      max_value = 86400,
      description = "Period for backup check invocations, in minutes."
    )

    self._event_bus_name = aws_cdk.CfnParameter(stack, "EventBusName",
      type = "String",
      default = "default",
      description = "Name of existing EventBridge bus for action events."
    )

    self._sns_topic_name = aws_cdk.CfnParameter(stack, "SnsTopicName",
      type = "String",
      default = "",
      description = "Name of existing SNS topic for action event notifications."
    )

    self._cloudwatch = aws_cdk.CfnParameter(stack, "CloudWatch",
      type = "String",
      default = "Disable",
      allowed_values = ["Enable", "Disable"],
      description = "Enable or disable CloudWatch dashboard and alarms."
    )
