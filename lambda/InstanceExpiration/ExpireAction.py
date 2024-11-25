"""
Helper class for the Instance Expiration lambda.
"""

# Copyright Amazon.com, Inc. and its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0



########################################################################################################################
# Imports
########################################################################################################################

import enum



########################################################################################################################
# Main Class
########################################################################################################################

class ExpireAction(enum.Enum):

  """ Enum for the possible actions upon EC2 instance expiration. """

  STOP = 1
  TERM = 2

  def __str__(self):
    return self.name
