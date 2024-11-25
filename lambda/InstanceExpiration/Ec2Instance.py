"""
EC2 instance class for use by the Instance Expiration lambda.
"""

# Copyright Amazon.com, Inc. and its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0



########################################################################################################################
# Imports
########################################################################################################################

import os
import re
import datetime
import logging

from ExpireAction import ExpireAction



########################################################################################################################
# Globals
########################################################################################################################

# Logging
LOG = logging.getLogger()

# Environment
IX_TAG_PREFIX = os.environ['IX_TAG_PREFIX']

# Other globals
STOP_AFTER_DURATION_TAG = IX_TAG_PREFIX + ':stop-after-duration'
STOP_AFTER_DATETIME_TAG = IX_TAG_PREFIX + ':stop-after-datetime'
TERM_AFTER_DURATION_TAG = IX_TAG_PREFIX + ':terminate-after-duration'
TERM_AFTER_DATETIME_TAG = IX_TAG_PREFIX + ':terminate-after-datetime'



########################################################################################################################
# Functions
########################################################################################################################

def TimeDeltaFromStr(duration):
  """
  Parse a duration string (ex: 1d2h3m4s) into a timedelta object. See: https://stackoverflow.com/a/51916936/22640509

  :param duration:              Duration string (ex: 1d2h3m4s).
  :return datetime.timedelta:   datetime.timedelta object, or 'None' if malformed duration string.
  """

  REGEX = re.compile(
    r'^((?P<days>[\.\d]+?)d)? *((?P<hours>[\.\d]+?)h)? *((?P<minutes>[\.\d]+?)m)? *((?P<seconds>[\.\d]+?)s)?$'
  )

  parts = REGEX.match(duration)

  td = None

  if parts is None:
    LOG.warning("Ignoring malformed duration string: %s", duration)
  else:
    td_params = {name: float(param) for name, param in parts.groupdict().items() if param}
    td = datetime.timedelta(**td_params)

  return td



def LesserOf(one, two):
  """
  Return the lesser of two values, with 'None' being the highest possible value.

  :param one:     First value.
  :param two:     Second value.
  :return:        Lessor of the two parameters, or 'None' if both values are 'None'.
  """

  if one is None:
    return two
  elif two is None:
    return one
  else:
    return min(one, two)



########################################################################################################################
# Main Class
########################################################################################################################

class Ec2Instance:
  """
  Concise representation of an EC2 instance relevant to the Instance Expiration Lambda.
  """

  @property
  def InstanceId(self):
    return self._instance_id

  @property
  def State(self):
    return self._state

  @property
  def ExpireAction(self):
    return self._expire_action

  @property
  def ExpireDateTime(self):
    return self._expire_date_time

  ADT_FMT = '%Y-%m-%d %H:%M:%S %Z'



  def __init__(self, instance):
    """
    Construct from a boto3 EC2.Instance.

    :param instance:    Boto3 EC2.Instance.
    """

    self._instance_id = instance['InstanceId']
    self._state = instance['State']['Name']

    sad  = self.GetDurationTagValue(instance, STOP_AFTER_DURATION_TAG)
    sadt = self.GetDateTimeTagValue(instance, STOP_AFTER_DATETIME_TAG)
    tad  = self.GetDurationTagValue(instance, TERM_AFTER_DURATION_TAG)
    tadt = self.GetDateTimeTagValue(instance, TERM_AFTER_DATETIME_TAG)

    sa = LesserOf(sad, sadt)
    ta = LesserOf(tad, tadt)

    self._expire_date_time = LesserOf(sa, ta)

    if not self._expire_date_time:
      LOG.warning("Ignoring EC2 instance with no properly formed expiration tags: %s", self._instance_id)
      self._expire_action = None
    elif self._expire_date_time == ta:
      self._expire_action = ExpireAction.TERM       # Term wins in a tie
    elif self._expire_date_time == sa:
      self._expire_action = ExpireAction.STOP
    else:
      assert False, "Logic error while processing EC2 instance '{}'.".format(self._instance_id)



  @staticmethod
  def GetTagValue(instance, tag_name):
    """
    Get the specified tag's value from a boto3 EC2.Instance object.

    :param instance:    Boto3 EC2.Instance object.
    :param tag_name:    Name of tag to retrieve.
    :return:            Tag value, or 'None' if not found.
    """

    if tag := list(filter(lambda x: x['Key'] == tag_name, instance['Tags'])):
      return tag[0]['Value']
    else:
      return None



  @staticmethod
  def GetDurationTagValue(instance, tag_name):
    """
    Get the specified tag's value from a boto3 EC2.Instance object, assuming it is a duration value and adding it to
    the instance's launch time to create an absolute datetime.

    :param instance:    Boto3 EC2.Instance object.
    :param tag_name:    Name of tag to retrieve.
    :return:            Datetime of tag value added to instance launch time, or 'None' if not found or invalid.
    """

    if d := Ec2Instance.GetTagValue(instance, tag_name):
      if o := TimeDeltaFromStr(d):
        return instance['LaunchTime'] + o
    return None



  @staticmethod
  def GetDateTimeTagValue(instance, tag_name):
    """
    Get the specified tag's value from a boto3 EC2.Instance object, assuming it is a datetime string matching the
    Ec2Instance.ADT_FMT format.

    :param instance:    Boto3 EC2.Instance object.
    :param tag_name:    Name of tag to retrieve.
    :return:            Datetime object, or 'None' if not found or invalid.
    """

    if dt := Ec2Instance.GetTagValue(instance, tag_name):
      try:
        return datetime.datetime.strptime(dt, Ec2Instance.ADT_FMT).replace(tzinfo = datetime.UTC)
      except Exception as ex:
        LOG.exception('Ignoring malformed datetime string: %s', dt)
    return None



  def __repr__(self):
    """
    :return:            Developer friendly string representation of this object.
    """

    return repr((self._instance_id, self._state, self._expire_action, self._expire_date_time.strftime(self.ADT_FMT)))
