> :memo: **Note:** You are responsible for the cost of the AWS services used while running this Guidance. As of
> October 2024, the cost for running this Guidance with the default settings in the US East (N. Virginia) region is
> approximately $0.15 per month for moderate usage volume.

# Costs Summary

The Instance Expiration guidance is very inexpensive to operate, even at high volume of usage, due to its event driven
design and use of serverless technologies.

Estimated monthly costs to operate by volume of usage, in USD rounded to the nearest penny, based on reasonable
assumptions of configuration:

* **Idle**: $0.00
* **Light**: $0.00
* **Moderate**: $0.15
* **Extreme**: $3.01

# Usage Volume

The cost to operate will vary by the following factors, with example values corresponding to the casual usage volume
labels in the summary section above:

(Values are per month)

| Factor                                       | Idle  | Light | Moderate | Extreme |
|----------------------------------------------|-------|-------|----------|---------|
| **EC2 instance starts**                      | 0     | 100   | 1000     | 10000   |
| **EC2 instance expiration tag changes**      | 0     | 100   | 1000     | 10000   |
| **Next schedule invocations**                | 0     | 300   | 3000     | 30000   |
| **Periodic schedule invocations**            | 730   | 730   | 730      | 730     |
| **Expiration actions**                       | 0     | 10    | 1000     | 10000   |
| **Average Lambda duration (ms)**             | 0     | 500   | 5000     | 100000  |
| **CloudWatch Log bytes / Lambda invocation** | 0     | 1 KB  | 10 KB    | 100 KB  |
| **Monthly Cost**                             | $0.00 | $0.00 | $0.05    | $3.01   |

These factors are primarily a function of:

1. Frequency of EC2 instance starts, which affects how often the Lambda executes.
2. Frequency of EC2 instance expiration tag changes, which affects how often the Lambda executes.
3. Number of EC2 instances present, which affects how many instances the Lambda must inspect during each execution.
4. Number of EC2 Instance expiration actions - i.e., whether actions are a safety net expected to occur rarely or are
expected frequently as a part of normal operations.

# Costs by AWS Service

The following table provides a sample cost breakdown for deploying this Guidance with the default parameters in the
US East (N. Virginia) Region for one month under moderate usage volume.

| AWS Service                | Dimensions                       | Cost [USD] |
|----------------------------|----------------------------------|------------|
| **Amazon EventBridge**     | Events and scheduler invocations | $0.00      |
| **Amazon SQS**             | Messages and data transfer       | $0.01      |
| **AWS Lambda**             | Requests and execution           | $0.10      |
| **Amazon SNS**             | Standard publishes               | $0.00      |
| **AWS Systems Manager**    | Parameters                       | $0.00      |
| **Amazon CloudWatch Logs** | Log ingestion and storage        | $0.03      |

# Cost Estimation Spreadsheet

See the provided [Cost Estimation Spreadsheet](instance-expiration-cost-estimate.xlsx) for the details, important
assumptions, and calculations for the above estimates.

Custom inputs can also be set in the spreadsheet for custom estimates.

# Optional CloudWatch Dashboard

If the `CloudWatch` parameter is set to `Enable` during deployment, a CloudWatch dashboard will be created with
metrics and logs emitted by this guidance.

The estimated cost for the CloudWatch dashboard is **$11.70 USD / month**, with details shown in the provided
[Cost Estimation Spreadsheet](instance-expiration-cost-estimate.xlsx).
