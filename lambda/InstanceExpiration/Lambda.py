"""
AWS Lambda to check for and handle EC2 instances that have run past their expiration tag values.
"""

# Copyright Amazon.com, Inc. and its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0



########################################################################################################################
# Imports
########################################################################################################################

import os
import datetime
import operator
import json
import logging
import boto3

from Ec2Instance import Ec2Instance
from ExpireAction import ExpireAction



########################################################################################################################
# Globals
########################################################################################################################

# Logging
LOG = logging.getLogger()
LOG.setLevel(logging.INFO)
#LOG.setLevel(logging.DEBUG)

# Boto clients
aws_ec2 = boto3.client('ec2')
aws_events = boto3.client('events')
aws_scheduler = boto3.client('scheduler')
aws_ssm = boto3.client('ssm')

# Environment
CFN_STACK_NAME = os.environ['CFN_STACK_NAME']
IX_TAG_PREFIX = os.environ['IX_TAG_PREFIX']
IX_STOP_ACTION = os.environ['IX_STOP_ACTION'] == "Enable"
IX_TERM_ACTION = os.environ['IX_TERM_ACTION'] == "Enable"
IX_EVENT_BUS_NAME = os.environ['IX_EVENT_BUS_NAME']
IX_SSM_PARAM_NEXT_SCHEDULE_ARN = os.environ['IX_SSM_PARAM_NEXT_SCHEDULE_ARN']



########################################################################################################################
# Functions
########################################################################################################################

def ResponseSuccessful(rsp):
  """
  Check a boto3 HTTP response for success.

  :param rsp:    Boto3 HTTP response object.
  :return:       True if HTTP response status code is 2xx; else False.
  """

  http_status_code = int( rsp['ResponseMetadata']['HTTPStatusCode'] )

  success = 200 <= http_status_code < 300

  if not success:
    LOG.warning(rsp)
  else:
    LOG.debug(rsp)

  return success



def PopNext(some_list):
  """
  Pop the next item from a list.

  :param some_list:   Any list.
  :return:            First element from the list or 'None' if the list is empty.
  """

  if len(some_list) != 0:
    return some_list.pop(0)
  else:
    return None



def PrepScheduleRequest(sch):
  """
  Must update schedule with current schedule object, minus some read-only fields.

  :param sch:   Schedule from GetSchedule API response.
  :return:      Input minus some fields illegal to supply to UpdateSchedule API.
  """

  sch.pop('ResponseMetadata', None)
  sch.pop('Arn', None)
  sch.pop('CreationDate', None)
  sch.pop('LastModificationDate', None)

  return sch



def CalculateNextCheck(inst):
  """
  Calculate the date/time of the next check. Normally use the expiration date/time of the given instance, but round
  up to at least X minutes from now to avoid trying to schedule in the past if the instance expiration date/time is
  very close to right now.

  :param inst:    Base on this instance's expiration date/time.
  :return:        Next check date/time.
  """

  no_sooner_than = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes = 1)

  if inst.ExpireDateTime < no_sooner_than:
    return no_sooner_than
  else:
    return inst.ExpireDateTime



def ScheduleNextCheck(inst):
  """
  Schedule the next time to run this Lambda.

  :param inst:  Next EC2 instance that will expire in the future.
  """

  try:

    LOG.info('Scheduling next check based on EC2 instance: ' + str(inst))

    rsp = aws_ssm.get_parameter(Name = IX_SSM_PARAM_NEXT_SCHEDULE_ARN)

    if ResponseSuccessful(rsp):
      schedule_name = rsp['Parameter']['Value'].split('/')[-1]
      schedule = aws_scheduler.get_schedule(Name = schedule_name)

      if ResponseSuccessful(schedule):
        schedule_at = CalculateNextCheck(inst)
        schedule['ScheduleExpression'] = 'at(' + schedule_at.strftime('%Y-%m-%dT%H:%M:%S') + ')'
        rsp = aws_scheduler.update_schedule(**PrepScheduleRequest(schedule))
        ResponseSuccessful(rsp)

  except Exception as ex:

    LOG.exception('Failed to schedule next check.')



def VerifyExpireAction(instance_id, expire_action):
  """
  Independently verify, to the extent practical, the planned action for an instance, in an attempt to catch any logic
  errors that were about to stop or terminate an EC2 instance incorrectly.

  :param instance_id:       EC2 instance id.
  :param expire_action:     Planned expiration action.
  :return:                  True to continue; False to abort.
  """

  result = False

  unexpected_instance_statuses = ['shutting-down', 'terminated']

  try:

    # Get instance metadata
    rsp = aws_ec2.describe_instances(InstanceIds = [instance_id])

    if ResponseSuccessful(rsp):

      # Choosing not to re-implement Ec2Instance logic as part of this verification...
      inst = Ec2Instance(rsp['Reservations'][0]['Instances'][0])

      # Verify
      assert inst.ExpireAction == expire_action
      assert inst.ExpireDateTime <= datetime.datetime.now(datetime.UTC)
      assert inst.State not in unexpected_instance_statuses

      assert ( (expire_action == ExpireAction.STOP) and IX_STOP_ACTION ) or \
             ( (expire_action == ExpireAction.TERM) and IX_TERM_ACTION )

      result = True

  except Exception as ex:

    LOG.exception("VerifyExpireAction(%s)", instance_id)

  return result



def EmitEventBusEvent(inst):
  """
  Emit an Amazon EventBridge event for a stop/term action.

  :param inst:              Expired EC2 instance.
  """

  if IX_EVENT_BUS_NAME != "":

    try:

      rsp = aws_events.put_events(Entries = [
        {
          'EventBusName': IX_EVENT_BUS_NAME,
          'Source': CFN_STACK_NAME,
          #'Resources': ...,                        # EC2 instance ARN is surprisingly difficult to get...
          'DetailType': 'Action',
          'Detail': json.dumps({
            'action': str(inst.ExpireAction),
            'instance-id': inst.InstanceId,
          }),
        }
      ])

      ResponseSuccessful(rsp)

    except Exception as ex:

      LOG.exception('Failed to emit event for action.')



def OnStopInstance(inst):
  """
  Stop an expired instance.

  :param inst:  Expired EC2 instance.
  """

  if not IX_STOP_ACTION:
    LOG.info("NOT stopping expired EC2 instance (StopAction disabled): %s",  inst.InstanceId)
  elif inst.State != 'running' and inst.State != 'pending':
    LOG.debug("NOT stopping expired EC2 instance (instance not running): %s",  inst.InstanceId)
  elif not VerifyExpireAction(inst.InstanceId, ExpireAction.STOP):
    LOG.error("Aborting stop of EC2 instance (failed verification): %s",  inst.InstanceId)
  else:
    rsp = aws_ec2.stop_instances(InstanceIds = [inst.InstanceId])
    if ResponseSuccessful(rsp):
      # The text of this log must match the StopActions CloudWatch logs metric filter.
      LOG.info("Stopped EC2 instance: %s",  inst.InstanceId)
      EmitEventBusEvent(inst)



def OnTermInstance(inst):
  """
  Terminate an expired instance.

  :param inst:  Expired EC2 instance.
  """

  if not IX_TERM_ACTION:
    LOG.info("NOT terminating expired EC2 instance (TerminateAction disabled): %s",  inst.InstanceId)
  elif not VerifyExpireAction(inst.InstanceId, ExpireAction.TERM):
    LOG.error("Aborting termination of EC2 instance (failed verification): %s",  inst.InstanceId)
  else:
    rsp = aws_ec2.terminate_instances(InstanceIds = [inst.InstanceId])
    if ResponseSuccessful(rsp):
      # The text of this log must match the TerminateActions CloudWatch logs metric filter.
      LOG.info("Terminated EC2 instance: %s",  inst.InstanceId)
      EmitEventBusEvent(inst)



def OnExpiredInstance(inst):
  """
  Handle an expired EC2 instance.

  :param inst:  Expired EC2 instance.
  """

  LOG.debug('Found expired EC2 instance: ' + str(inst))

  try:
    if inst.ExpireAction == ExpireAction.STOP:
      OnStopInstance(inst)
    elif inst.ExpireAction == ExpireAction.TERM:
      OnTermInstance(inst)
    else:
      assert False, "Unexpected ExpireAction '{}'.".format(inst.ExpireAction)
  except Exception as ex:
    LOG.exception("Failed to handle expired EC2 instance: %s", inst.InstanceId)



########################################################################################################################
# Handler
########################################################################################################################

def handler(event, context):

  try:

    LogTrigger(event, context)

    #
    # Iterate over all in-scope EC2 instances, collecting into a succinct list.
    #

    instance_filter = [
      {
        # Omitting 'shutting-down', 'terminated'
        'Name': 'instance-state-name',
        'Values': ['pending', 'running', 'stopping', 'stopped']
      },
      {
        # Limiting to instances with at least one expiration tag
        'Name': 'tag-key',
        'Values': [IX_TAG_PREFIX + ':*']
      }
    ]

    instances = []

    for page in aws_ec2.get_paginator('describe_instances').paginate(Filters = instance_filter):
      for res in page['Reservations']:
        for inst in res['Instances']:
          try:
            instances.append(Ec2Instance(inst))
          except Exception as ex:
            LOG.exception("Ignoring EC2 instance that failed to parse: %s", inst['InstanceId'])

    #
    # Sort resulting list by the next expiration date/time (soonest first).
    #

    instances.sort(key = operator.attrgetter('ExpireDateTime'))

    LOG.debug(str(instances))

    #
    # Handle expired instances and schedule check based on next instance expected to expire.
    #

    while i := PopNext(instances):
      if i.ExpireDateTime <= datetime.datetime.now(datetime.UTC):
        OnExpiredInstance(i)
      else:
        ScheduleNextCheck(i)
        break

  except Exception as ex:

    LOG.exception("handler()")



########################################################################################################################
# Pure Logging
########################################################################################################################

def LogTriggerSource(name, event = None):

  LOG.info('Trigger: %s', name)

  if event:
    LOG.info('Lambda event: ' + json.dumps(event))



def LogTrigger(event, context):

  try:

    LOG.debug('Lambda context: ' + str(context))
    LOG.debug('Lambda event: ' + json.dumps(event))

    LOG.debug('Tag Prefix: ' + str(IX_TAG_PREFIX))
    LOG.debug('Stop Action: ' + str(IX_STOP_ACTION))
    LOG.debug('Term Action: ' + str(IX_TERM_ACTION))
    LOG.debug('Event Bus Name: ' + str(IX_EVENT_BUS_NAME))

    if not (records := event.get('Records')) or not len(records):
      LogTriggerSource('Unknown', event)
    else:
      for rec in records:
        try:
          body = json.loads(rec['body'])
          detail_type = body['detail-type']
          resource = body['resources'][0]
          if detail_type == 'Tag Change on Resource':
            LogTriggerSource('EC2 Instance Expiration Tag Change (' + resource + ')')
          elif detail_type == 'EC2 Instance State-change Notification':
            LogTriggerSource('EC2 Instance State Change (' + resource + ')')
          elif detail_type == 'Scheduled Event':
            if 'NextSchedule' in resource:
              LogTriggerSource('Next Schedule')
            elif 'RateSchedule' in resource:
              LogTriggerSource('Backup Schedule')
            else:
              LogTriggerSource('Unknown', event)
          else:
            LogTriggerSource('Unknown', event)
        except Exception as ex:
          LogTriggerSource('Unknown', event)

  except Exception as ex:

    LOG.exception('LogTrigger()')
