"""
AWS Cloud Development Kit (CDK) construct for CloudWatch resources for the stack.
"""

# Copyright Amazon.com, Inc. and its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0



########################################################################################################################
# Imports
########################################################################################################################

from aws_cdk import (
  aws_cloudwatch,
  aws_logs,
  Stack,
)

from aws_cdk.aws_cloudwatch import (
  Color,
  Stats,
)

from constructs import Construct



########################################################################################################################
# Main Class
########################################################################################################################

class CloudWatch(Construct):
  """
  Creates CloudWatch resources for the stack.
  """



  def __init__(self, scope: Construct, construct_id: str,
               ix_lambda, ix_dlq, ix_queue, ix_sched_group, ix_tag_rule, ix_start_rule, **kwargs) -> None:
    """
    :param ix_lambda:        aws_cdk.aws_lambda.Function
    :param ix_dlq:           aws_cdk.aws_sqs.Queue
    :param ix_queue:         aws_cdk.aws_sqs.Queue
    :param ix_sched_group:   Schedule group name (string)
    :param ix_tag_rule:      aws_cdk.aws_events.Rule
    :param ix_start_rule:    aws_cdk.aws_events.Rule
    """

    super().__init__(scope, construct_id)

    self._ix_tag_rule    = ix_tag_rule
    self._ix_start_rule  = ix_start_rule
    self._ix_dlq         = ix_dlq
    self._ix_queue       = ix_queue
    self._ix_sched_group = ix_sched_group
    self._ix_lambda      = ix_lambda

    #
    # CloudWatch Dashboard
    #

    ix_cw_dashboard = aws_cloudwatch.Dashboard(self, "Dashboard",
      dashboard_name = Stack.of(self).stack_name + 'Dashboard',
    )

    #
    # Amazon EventBridge Rule Metrics
    #

    ix_cw_dashboard.add_widgets(
      aws_cloudwatch.GraphWidget(
        title = "EC2 Tag Rule",
        width = 24,
        left = [
          self.RuleMetric(ix_tag_rule, "Invocations", Stats.SUM, Color.GREEN),
          self.RuleMetric(ix_tag_rule, "MatchedEvents", Stats.SUM, Color.BLUE),
          self.RuleMetric(ix_tag_rule, "FailedInvocations", Stats.SUM, Color.RED),
        ],
      )
    )

    ix_cw_dashboard.add_widgets(
      aws_cloudwatch.GraphWidget(
        title = "EC2 Start Rule",
        width = 24,
        left = [
          self.RuleMetric(ix_start_rule, "Invocations", Stats.SUM, Color.GREEN),
          self.RuleMetric(ix_start_rule, "MatchedEvents", Stats.SUM, Color.BLUE),
          self.RuleMetric(ix_start_rule, "FailedInvocations", Stats.SUM, Color.RED),
        ],
      )
    )

    #
    # Amazon EventBridge Scheduler Group Metrics
    #

    ix_cw_dashboard.add_widgets(
      aws_cloudwatch.GraphWidget(
        title = "Schedulers",
        width = 24,
        left = [
          self.SchedulerMetric("InvocationAttemptCount", Stats.SUM, Color.GREEN),
          self.SchedulerMetric("TargetErrorCount", Stats.SUM, Color.RED),
          self.SchedulerMetric("TargetErrorThrottledCount", Stats.SUM, Color.ORANGE),
          self.SchedulerMetric("InvocationThrottleCount", Stats.SUM, Color.PINK),
          self.SchedulerMetric("InvocationDroppedCount", Stats.SUM, Color.PURPLE),
        ],
      )
    )

    #
    # Amazon SQS Queue Metrics
    #

    ix_cw_dashboard.add_widgets(
      aws_cloudwatch.GraphWidget(
        title = "Queue",
        width = 24,
        left = [
          ix_queue.metric_number_of_messages_sent(statistic = Stats.SUM, color = Color.GREEN),
          ix_queue.metric_number_of_messages_received(statistic = Stats.SUM, color = Color.BLUE),
          ix_queue.metric_approximate_number_of_messages_visible(statistic = Stats.MAXIMUM, color = Color.BROWN),
        ],
        right = [
          ix_queue.metric_approximate_age_of_oldest_message(statistic = Stats.MAXIMUM, color = Color.GREY),
        ],
      )
    )

    ix_cw_dashboard.add_widgets(
      aws_cloudwatch.GraphWidget(
        title = "Dead Letter Queue",
        width = 24,
        left = [
          ix_dlq.metric_number_of_messages_sent(statistic = Stats.SUM, color = Color.GREEN),
          ix_dlq.metric_number_of_messages_received(statistic = Stats.SUM, color = Color.BLUE),
          ix_dlq.metric_approximate_number_of_messages_visible(statistic = Stats.MAXIMUM, color = Color.BROWN),
        ],
        right = [
          ix_dlq.metric_approximate_age_of_oldest_message(statistic = Stats.MAXIMUM, color = Color.GREY),
        ],
      )
    )

    #
    # AWS Lambda Metrics
    #

    ix_cw_dashboard.add_widgets(
      aws_cloudwatch.GraphWidget(
        title = "Lambda Invocations",
        width = 24,
        left = [
          ix_lambda.metric_invocations(statistic = Stats.SUM, color = Color.GREEN),
          ix_lambda.metric_throttles(statistic = Stats.SUM, color = Color.ORANGE),
          ix_lambda.metric_errors(statistic = Stats.SUM, color = Color.RED),
        ],
      )
    )

    ix_cw_dashboard.add_widgets(
      aws_cloudwatch.GraphWidget(
        title = "Lambda Duration",
        width = 24,
        left = [
          ix_lambda.metric_duration(statistic = Stats.MINIMUM, color = Color.GREEN),
          ix_lambda.metric_duration(statistic = Stats.AVERAGE, color = Color.BLUE),
          ix_lambda.metric_duration(statistic = Stats.MAXIMUM, color = Color.ORANGE),
        ]
      )
    )

    ix_cw_dashboard.add_widgets(
      aws_cloudwatch.LogQueryWidget(
        title = 'Lambda Memory Used (MB)',
        width = 24,
        log_group_names = [ix_lambda.log_group.log_group_name],
        view = aws_cloudwatch.LogQueryVisualizationType.LINE,
        query_lines = [
          'filter @type = "REPORT"',
          # Cannot specify color for each, so must use the order here to control colors assigned.
          'stats'
          + ' avg(@maxMemoryUsed / 1000 / 1000) as AvgUsed,'                # Blue
          + ' max(@maxMemoryUsed / 1000 / 1000) as MaxUsed,'                # Orange
          + ' min(@maxMemoryUsed / 1000 / 1000) as MinUsed'                 # Green
          + ' by bin(1h)',
          ],
      )
    )

    ix_cw_dashboard.add_widgets(
      aws_cloudwatch.LogQueryWidget(
        title = 'Lambda Memory Free (%)',
        width = 24,
        log_group_names = [ix_lambda.log_group.log_group_name],
        view = aws_cloudwatch.LogQueryVisualizationType.LINE,
        query_lines = [
          'filter @type = "REPORT"',
          'stats'
          + ' 100 - ( max(@maxMemoryUsed / 1000 / 1000) / max(@memorySize / 1000 / 1000) * 100 ) as PercentFree'
          + ' by bin(1h)',
        ],
      )
    )

    #
    # Application Log Metrics
    #

    ix_cw_dashboard.add_widgets(
      aws_cloudwatch.GraphWidget(
        title = "App Log Metrics",
        width = 24,
        left = [
          self.AppLogMetric('StopActions', '"Stopped EC2 instance: "', Stats.SUM, Color.GREY),
          self.AppLogMetric('TerminateActions', '"Terminated EC2 instance: "', Stats.SUM, Color.BROWN),
          self.AppLogMetric('Warnings', '"[WARNING]"', Stats.SUM, Color.ORANGE),
          self.AppLogMetric('Errors', '"[ERROR]"', Stats.SUM, Color.RED),
        ]
      )
    )

    #
    # Application Log Queries
    #

    ix_cw_dashboard.add_widgets(
      aws_cloudwatch.LogQueryWidget(
        title = 'App Action Logs',
        width = 24,
        log_group_names = [ix_lambda.log_group.log_group_name],
        view = aws_cloudwatch.LogQueryVisualizationType.TABLE,
        query_lines = [
          'fields @timestamp, @message',
          'filter (@message like "Stopped EC2 instance: " or @message like "Terminated EC2 instance: ")',
          'sort @timestamp desc'
        ],
      )
    )

    ix_cw_dashboard.add_widgets(
      aws_cloudwatch.LogQueryWidget(
        title = 'App Warning and Error Logs',
        width = 24,
        log_group_names = [ix_lambda.log_group.log_group_name],
        view = aws_cloudwatch.LogQueryVisualizationType.TABLE,
        query_lines = [
          'fields @timestamp, @message',
          'filter (@message like "[WARNING]" or @message like "[ERROR]")',
          'sort @timestamp desc'
        ],
      )
    )



  @staticmethod
  def RuleMetric(rule, name, statistic, color):
    """
    Construct and return an Amazon EventBridge Rule metric.
    """

    m = aws_cloudwatch.Metric(
      namespace = "AWS/Events",
      metric_name = name,
      statistic = statistic,
      color = color,
      dimensions_map = {
        "RuleName": rule.rule_name
      },
    )

    return m



  def SchedulerMetric(self, name, statistic, color):
    """
    Construct and return an Amazon EventBridge Scheduler metric.
    """

    m = aws_cloudwatch.Metric(
      namespace = "AWS/Scheduler",
      metric_name = name,
      statistic = statistic,
      color = color,
      dimensions_map = {
        "ScheduleGroup": self._ix_sched_group,
      },
    )

    return m



  def AppLogMetric(self, name, pattern, statistic, color):
    """
    Construct and return an Amazon CloudWatch log metric.
    """

    mf = self._ix_lambda.log_group.add_metric_filter("LambdaLogMetricFilter" + name,
      metric_namespace = Stack.of(self).stack_name,
      metric_name = name,
      filter_pattern = aws_logs.FilterPattern.literal(pattern),
      unit = aws_cloudwatch.Unit.COUNT,
      default_value = 0,
      metric_value = '1',
    )

    m = mf.metric(
      statistic = statistic,
      color = color,
    )

    return m
