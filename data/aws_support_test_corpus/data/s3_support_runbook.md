# Amazon S3 Support Runbook

> Lab document: synthetic operational guidance for ingestion and retrieval
> testing. Replace example names before using commands.

## Incident S3-01: recover an accidentally deleted object

### Symptom

The application receives `404 Not Found` for
`s3://support-lab-artifacts/index.html` after an operator issued a delete
request. The bucket had S3 Versioning enabled before the deletion.

### Diagnosis

A simple delete request that does not include a version ID does not permanently
remove an object from a versioning-enabled bucket. Amazon S3 creates a delete
marker and makes that marker the current version. The older object version
remains stored as a noncurrent version.

List the versions and delete markers:

```bash
aws s3api list-object-versions \
  --bucket support-lab-artifacts \
  --prefix index.html
```

Confirm that the newest entry for the key is a delete marker and record its
`VersionId`. Do not delete an older data-bearing version.

### Recovery

Delete the delete marker by specifying the marker's version ID:

```bash
aws s3api delete-object \
  --bucket support-lab-artifacts \
  --key index.html \
  --version-id DELETE_MARKER_VERSION_ID
```

After the marker is removed, the previous object version becomes current and a
normal `GetObject` request can return the object again. If the actual
data-bearing version was permanently deleted with its version ID, S3 cannot
recover that version.

## Incident S3-02: diagnose `403 AccessDenied`

### First decision

An S3 `403 AccessDenied` response means authorization ended in either an
explicit deny or an implicit deny. An explicit `Deny` in an applicable policy
overrides an `Allow`. An implicit deny means that no applicable statement
allowed the requested action.

Record the principal ARN, bucket, object key, requested action, Region, request
time, and AWS request ID. Use the enhanced access-denied message when it is
available, then inspect CloudTrail for the same request.

### Authorization checklist

Review every policy layer that can affect the request:

1. The principal's identity-based IAM policies.
2. The S3 bucket or access-point resource policy.
3. AWS Organizations service control policies.
4. A permissions boundary or STS session policy.
5. A VPC endpoint policy when the request uses an endpoint.
6. The KMS key policy when the object uses SSE-KMS.
7. Object Ownership and legacy ACL configuration when ownership differs.

Do not “fix” the incident by adding broad `s3:*` permissions. Find the policy
that denied the exact action and resource, make the smallest justified change,
and retest with the same principal and request path.

| Signal | Likely investigation |
|---|---|
| `GetObject` fails but `ListBucket` works | Object ARN, object ownership, KMS permissions |
| Requests through a VPC endpoint fail | Endpoint policy and bucket-policy conditions |
| All principals in one member account fail | AWS Organizations SCP |
| Only temporary role sessions fail | Session policy and permissions boundary |

## Source references

- AWS S3 troubleshooting:
  <https://docs.aws.amazon.com/AmazonS3/latest/userguide/troubleshoot-403-errors.html>
- AWS S3 versioning troubleshooting:
  <https://docs.aws.amazon.com/AmazonS3/latest/userguide/troubleshooting-versioning.html>
