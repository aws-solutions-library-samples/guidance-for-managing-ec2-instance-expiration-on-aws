#!/usr/bin/env python3

"""
Post-process the synthesized output (CloudFormation template) of the AWS CDK for this CDK app.

Post-processing of the AWS CDK synth output is usually not necessary. However, this app encounters an AWS CDK bug
whereby some CloudFormation template keys are incorrectly converted from upper-camel-case to lower-camel-case, causing
validation errors when deploying the resulting template. This post-processing script fixes the template.

This script is invoked automatically after the 'cdk synth' step by virtue of its inclusion in the 'app' element of
the project's 'cdk.json' file.

See:
- https://github.com/aws/aws-cdk/issues/8996
- https://stackoverflow.com/questions/56835557/aws-cdk-post-deployment-actions
"""

# Copyright Amazon.com, Inc. and its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0



########################################################################################################################
# Imports
########################################################################################################################

import os
import sys
import json



########################################################################################################################
# Confirm required Python version.
########################################################################################################################

if sys.version_info < (3, 6):
  print("Detected Python version ", sys.version_info.major, ".", sys.version_info.minor, sep='', end='')
  print(", but this script requires Python 3.6+. Aborting.")
  exit()



########################################################################################################################
# Global Constants
########################################################################################################################

CFN_FILE_NAME = os.path.join('cdk.out', 'InstanceExpiration.template.json')
CFN_FILE_ENC = 'utf-8'

KEYS_TO_UCC = ['id', 'arn', 'inputTransformer', 'inputTemplate', 'inputPathsMap']



########################################################################################################################
# Functions
########################################################################################################################

def Status(s):

  print(os.path.basename(__file__) + ': ' + s)



def KeyToUcc(k):

  if k in KEYS_TO_UCC:
    return k[:1].upper() + k[1:]
  else:
    return k



def FindKeysToUcc(cfn_json):

  if isinstance(cfn_json, dict):
    return {KeyToUcc(key): FindKeysToUcc(value) for key, value in cfn_json.items()}

  elif isinstance(cfn_json, list):
    return [FindKeysToUcc(item) for item in cfn_json]

  return cfn_json



########################################################################################################################
# Main Script
########################################################################################################################

def main():

  try:

    Status('...')

    # Open the synthesized output (CloudFormation template).
    with open(CFN_FILE_NAME, 'r', encoding = CFN_FILE_ENC) as cfn_file:
      cfn_json_orig = json.load(cfn_file)

    # Post-process.
    cfn_json_new = FindKeysToUcc(cfn_json_orig)

    # Rewrite with the modified JSON.
    with open(CFN_FILE_NAME, 'w', encoding = CFN_FILE_ENC) as cfn_file:
      json.dump(cfn_json_new, cfn_file, indent = 1)

    Status('.')

  except Exception as ex:

    Status(str(ex))
    raise



########################################################################################################################
# See: https://docs.python.org/3/library/__main__.html#idiomatic-usage
########################################################################################################################

if __name__ == '__main__':
  sys.exit(main())
