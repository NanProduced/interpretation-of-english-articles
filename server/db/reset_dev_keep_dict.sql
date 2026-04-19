BEGIN;

TRUNCATE TABLE
  analysis_audit_logs,
  analysis_task_events,
  analysis_tasks,
  analysis_results,
  favorite_records,
  vocabulary_book,
  user_credit_ledger,
  user_credit_accounts,
  user_sessions,
  user_identities,
  analysis_records,
  anonymous_quotas,
  users
RESTART IDENTITY CASCADE;

COMMIT;
