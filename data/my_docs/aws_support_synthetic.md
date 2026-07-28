# Synthetic AWS Support Troubleshooting Notes

> This document is a synthetic evaluation fixture created for an ingestion-pipeline
> assignment. It is not an AWS support response and should not replace current AWS
> documentation in production.

## Amazon S3 403 AccessDenied

A customer can list some buckets but receives HTTP 403 AccessDenied when reading an
object. First identify the rejected API action, requester, resource owner, and whether
the denial is explicit or implicit.

For an Amazon S3 403 AccessDenied response, review the IAM identity policy, bucket
policy, VPC endpoint policy, S3 Block Public Access settings, and the AWS KMS key
policy for KMS-encrypted objects.

Check the enhanced access-denied message when it is available, then test the effective
permissions without weakening public-access protections.

## Amazon EC2 Status Check Failure

An operations dashboard reports an impaired EC2 instance. The team must distinguish
an AWS-host problem from a problem inside the guest before choosing a recovery action.

An EC2 system status check failure indicates a problem with the underlying AWS
infrastructure, while an instance status check failure indicates a problem with the
guest operating system or its network configuration.

For a system check failure on an EBS-backed instance, a stop and start can move the
instance to a new host. For an instance check failure, inspect boot logs, memory,
filesystem, and network configuration.

## AWS Lambda Timeout

A Lambda function reaches its configured timeout during requests to a downstream
service. Increasing the timeout immediately can hide the cause, so observability and
dependency checks should come first.

To diagnose an AWS Lambda timeout, inspect the CloudWatch REPORT duration and logs,
AWS X-Ray traces, downstream-service latency, VPC and NAT network routes, and the
function's memory allocation.

Compare successful and failed invocations, verify that SDK calls use bounded timeouts,
and confirm that the execution role can publish logs and traces.

## Amazon RDS Proxy for Bursty Lambda Workloads

A serverless application opens many short-lived database connections when concurrent
Lambda invocations rise suddenly. The database reaches its connection limit even
though individual queries are short.

Amazon RDS Proxy helps bursty Lambda workloads by pooling and reusing database
connections, reducing connection churn and the number of simultaneous connections
that reach the database.

The application must still configure suitable transaction behavior, connection
timeouts, database capacity, network access, and credentials.

## Amazon CloudFront Content Updates

A web team deploys static assets several times per day. Reusing the same object name
can leave an older object in browser, proxy, or CloudFront caches until it expires.

For frequent CloudFront deployments, use versioned object names because versioning
controls which revision clients request, simplifies rollbacks, and avoids repeated
invalidation charges.

Invalidation remains useful when content must be removed before its normal cache
expiration, but it should not be the default release mechanism for frequently changed
assets.
