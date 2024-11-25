#!/usr/bin/env python3

"""
AWS Cloud Development Kit (CDK) app for AWS Solutions Library 'Guidance for Instance Expiration on AWS'.
"""

# Copyright Amazon.com, Inc. and its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0



########################################################################################################################
# Documentation
########################################################################################################################

# See the README.md file.



########################################################################################################################
# Imports
########################################################################################################################

#import os
import sys
import aws_cdk
import cdk_nag

from instance_expiration.Stack import Stack



########################################################################################################################
# Confirm required Python version.
########################################################################################################################

if sys.version_info < (3, 9):
  print("Detected Python version ", sys.version_info.major, ".", sys.version_info.minor, sep='', end='')
  print(", but this script requires Python 3.9+. Aborting.")
  exit()



########################################################################################################################
# Main Script
########################################################################################################################

app = aws_cdk.App()

Stack(app, "InstanceExpiration",
  # If you don't specify 'env', this stack will be environment-agnostic.
  # Account/Region-dependent features and context lookups will not work,
  # but a single synthesized template can be deployed anywhere.

  # Uncomment the next line to specialize this stack for the AWS Account
  # and Region that are implied by the current CLI configuration.

  #env = aws_cdk.Environment(account = os.getenv('CDK_DEFAULT_ACCOUNT'), region = os.getenv('CDK_DEFAULT_REGION')),

  # Uncomment the next line if you know exactly what Account and Region you
  # want to deploy the stack to.

  #env = aws_cdk.Environment(account = '123456789012', region = 'us-east-1'),

  # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
)

aws_cdk.Aspects.of(app).add(cdk_nag.AwsSolutionsChecks())

app.synth()
