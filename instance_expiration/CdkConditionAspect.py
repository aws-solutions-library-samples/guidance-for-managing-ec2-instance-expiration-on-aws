"""
AWS CDK IAspect for applying a CfnCondition to the resources of a construct.
"""

# Copyright Amazon.com, Inc. and its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0



########################################################################################################################
# Imports
########################################################################################################################

import jsii
import aws_cdk



########################################################################################################################
# Main Class
########################################################################################################################

@jsii.implements(aws_cdk.IAspect)
class CdkConditionAspect:
  """
  See:
  - https://github.com/aws/aws-cdk/issues/1591
  - https://docs.aws.amazon.com/cdk/v2/guide/aspects.html
  """

  def __init__(self, cond) -> None:
    """
    :param cond:    aws_cdk.CfnCondition object.
    """
    self._cond = cond

  def visit(self, node) -> None:
    if isinstance(node, aws_cdk.CfnResource):
      node.cfn_options.condition = self._cond
