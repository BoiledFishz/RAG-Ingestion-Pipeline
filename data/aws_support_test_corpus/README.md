# AWS Support Ingestion Test Corpus

This is a synthetic, test-only corpus for validating a production-style RAG
ingestion pipeline. It is not an official AWS support publication.

## Included files

| Path | Purpose | Expected behavior |
|---|---|---|
| `data/s3_support_runbook.md` | Clean Markdown with headings, lists, a table, and commands | Parse normally and preserve useful Markdown structure |
| `data/lambda_support_notes.md` | Markdown containing HTML and image/link noise | `clean_text` removes presentation noise but keeps support facts |
| `data/ec2_network_connectivity.pdf` | Two-page text PDF | Extract text directly and retain page numbers 1 and 2 |
| `data/iam_access_recovery_scanned.pdf` | Two-page image-only PDF | Direct extraction returns no useful text; OCR fallback should run |
| `data/empty_document.md` | Empty/whitespace-only input | Return an empty document list without raising |
| `data/corrupt_document.pdf` | Deliberately truncated invalid PDF | Log a warning and return an empty document list |
| `eval/golden_set.json` | Five question-ground-truth pairs | Retrieve contexts and compute Context Recall |
| `manifest.json` | Machine-readable expectations | Useful for integration tests and demonstrations |

## Suggested validation

Run the ingestion pipeline twice against the same vector collection.

On the first run:

- Four useful documents should be ingested.
- The empty Markdown and corrupt PDF should be skipped safely.
- OCR should be called only for `iam_access_recovery_scanned.pdf`.
- Every chunk should contain `source_file`, `page_number`, `chunk_hash`, and
  `context_summary`.

On the second run:

- Every existing `chunk_hash` should be detected before summary and embedding
  requests.
- No duplicate vectors should be created.
- No repeated summary or embedding charge should be incurred.

For the chunking experiment, use separate vector collections for `256` and
`512` so that the retrieval results cannot mix.

## Golden-set mapping

| ID | Topic | Expected source |
|---|---|---|
| Q1 | Recovering a deleted S3 object | `s3_support_runbook.md` |
| Q2 | Diagnosing an S3 403 | `s3_support_runbook.md` |
| Q3 | Lambda concurrency isolation | `lambda_support_notes.md` |
| Q4 | EC2 public IPv4 internet access | `ec2_network_connectivity.pdf`, page 1 |
| Q5 | IAM permissions boundaries | `iam_access_recovery_scanned.pdf`, page 1 |

## Reference material

The synthetic facts were checked against the AWS documentation pages listed in
the source documents. The wording was written specifically for this test
corpus; it is not copied from AWS documentation.
