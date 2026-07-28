<!-- top-navigation: home / services / lambda / operations -->
<div class="training-banner">INTERNAL TRAINING COPY - DO NOT INDEX THIS BANNER</div>

# AWS Lambda Operations Notes

![Decorative architecture image](./images/lambda-overview.png)

## Case LAMBDA-01: one function consumes the concurrency pool

### Symptoms

Several unrelated functions begin returning throttling errors while
`order-exporter` shows a sharp rise in the CloudWatch `ConcurrentExecutions`
metric. The regional pool has little unreserved concurrency left.

### Response

Configure **reserved concurrency** for functions that need isolation. Reserved
concurrency creates a dedicated concurrency allocation for a function and also
caps that function at the configured value. This prevents one function from
scaling without limit and consuming the concurrency needed by other functions.

Use CloudWatch `ConcurrentExecutions`, `UnreservedConcurrentExecutions`, and
`Throttles` to validate the diagnosis. A value of zero for a function's reserved
concurrency intentionally stops that function from processing events.

Reserved concurrency is a capacity control; it does not pre-initialize
environments. Provisioned concurrency is the separate feature used when the
goal is to reduce cold-start latency.

## Case LAMBDA-02: function reaches its timeout

The timeout setting is the maximum time a Lambda invocation may run. Before
raising it, inspect the CloudWatch duration distribution and downstream
latency. Test with realistic upper-bound payload sizes because small test
events can hide slow S3 downloads or slow service calls.

Set a timeout with enough margin above normal high-percentile duration, but do
not use a larger timeout to conceal an unbounded retry or network call. Add
client-side timeouts to downstream calls and make retry behavior explicit.

Example:

```bash
aws lambda update-function-configuration \
  --function-name order-exporter \
  --timeout 120
```

Lambda's configurable timeout range is 1 through 900 seconds.

## Case LAMBDA-03: recursive invocation

An S3 notification can invoke a function that writes another object into the
same triggering bucket. Without a prefix, suffix, or separate destination, the
new object can invoke the function again and create a loop. Use separate input
and output locations or apply an event filter. If a loop is active and impact
is growing, setting reserved concurrency to zero is an emergency way to stop
new executions while the event configuration is corrected.

<footer>Generated for pipeline testing. Last reviewed: 2026-07-28.</footer>

## Source references

- [Lambda invocation troubleshooting](https://docs.aws.amazon.com/lambda/latest/dg/troubleshooting-invocation.html)
- [Lambda timeout configuration](https://docs.aws.amazon.com/lambda/latest/dg/configuration-timeout.html)
