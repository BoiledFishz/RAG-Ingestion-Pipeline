# AWS Support Knowledge Base Sample

This synthetic document is included only so the ingestion and retrieval benchmark can be
reproduced without downloading proprietary support content. Production deployments should
replace it with approved AWS documentation and internal runbooks.

## Amazon S3 AccessDenied troubleshooting

An Amazon S3 HTTP 403 AccessDenied response means that authorization failed before the
requested object operation completed. Permission denial can result from an IAM identity
policy, bucket policy, VPC endpoint policy, AWS KMS key policy, or S3 Block Public Access.
Inspect every applicable policy because an explicit deny overrides an allow. For an object
encrypted with an AWS KMS customer managed key, the caller also needs permission to use the
key. Compare the principal, resource ARN, action, and condition keys in CloudTrail with the
policies that apply to the request. Do not fix this symptom by broadly granting public access.

## Amazon EC2 status checks

EC2 performs system status checks and instance status checks every minute. A failed system
status check points to an AWS infrastructure problem such as loss of network connectivity,
host power, or host hardware. A failed instance status check points to the guest operating
system, exhausted memory, a corrupted file system, or incorrect network configuration.
For an EBS-backed instance with a system status failure, a stop and start commonly moves the
instance to healthy hardware. For an instance status failure, review the system log and use
EC2 Serial Console or a rescue instance before changing infrastructure.

## AWS Lambda timeout diagnosis

The Lambda timeout setting limits how long one invocation may run and can be configured up
to the service maximum. Diagnose a timeout with the REPORT line duration, CloudWatch Logs,
AWS X-Ray traces, and downstream latency metrics. Increasing the timeout only masks the
problem when a function waits on an unreachable dependency. Reuse SDK clients outside the
handler, set shorter connection and read timeouts on downstream calls, and verify that a
VPC-attached function has a route to every required endpoint. Also check memory because more
memory allocates proportionally more CPU and can shorten compute-bound invocations.

## Amazon RDS connection exhaustion

An RDS database can reject new sessions when the engine reaches its max_connections limit
or when memory pressure prevents another backend process. Check DatabaseConnections,
FreeableMemory, CPUUtilization, and engine logs before changing a parameter group. RDS Proxy
pools and reuses database connections, which is especially useful for bursty Lambda workloads.
Applications must still close connections, bound their client pools, and apply exponential
backoff. Raising max_connections without enough memory can make the database less stable.

## Amazon CloudFront cache invalidation

A CloudFront invalidation removes selected cached paths from edge locations before their
normal expiration. Use a versioned object name for frequent releases because versioning is
usually faster, cheaper, and easier to roll back than repeated invalidations. An invalidation
path begins with a slash, and a trailing wildcard can cover every object below a prefix.
CloudFront continues serving the old object until the invalidation reaches an edge location,
so monitor invalidation status before assuming that every viewer receives the new version.
