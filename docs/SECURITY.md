# SECURITY.md

## Trust Boundaries
- Source documents and generated outputs may contain confidential customer data.
- Provider API calls (e.g., Gemini Developer API) transmit potentially sensitive prompt and output content.
- Evaluation results stored in Firestore may expose business-sensitive weaknesses if payload storage is not redacted.

## Security Rules
- Never commit secrets (`GEMINI_API_KEY`) or service-account JSON files.
- Use Cloud Run environment variables or Secret Manager to pass the `GEMINI_API_KEY`.
- The system defaults to **redacting input and output payloads** when saving run history to Firestore. To persist these payloads intentionally, the client must explicitly send `store_full_payloads: true` in the request.

## Runtime Authentication
- **Gemini Judge:** Uses Developer API Mode requiring `GEMINI_API_KEY`.
- **Firestore:** Relies exclusively on Application Default Credentials (ADC) via Cloud Run identities or `gcloud auth application-default login` for local execution.

## GCP Posture
For production deployment, prefer:
- Cloud Run for service hosting
- Secret Manager for API keys
- IAM-scoped service accounts for the Cloud Run identity to access Firestore
- BigQuery export purely for analytical/historical aggregation

## Future Security Work
- request authentication / authorization for API mode
- payload retention policies on Firestore
- audit logs for evaluation and promotion decisions
- PII-aware redaction for judge provider calls (before sending text to Gemini)
