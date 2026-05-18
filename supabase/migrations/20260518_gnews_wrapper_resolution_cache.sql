-- Persistent cache for Google-News wrapper URL resolution.
-- Additive and idempotent. Caches positive AND negative results so the
-- resolver never re-hits the same dead/blocked URL.

CREATE TABLE IF NOT EXISTS gnews_wrapper_resolution (
    original_url       text PRIMARY KEY,
    resolved_url       text,
    status             text NOT NULL,
    failure_reason     text,
    first_seen_at      timestamptz NOT NULL DEFAULT now(),
    last_attempted_at  timestamptz NOT NULL DEFAULT now(),
    resolved_at        timestamptz,
    attempts           integer NOT NULL DEFAULT 1,
    runtime_ms         integer,
    resolver_version   text,
    source_domain      text,
    final_domain       text
);

CREATE INDEX IF NOT EXISTS idx_gnews_wrapper_status
    ON gnews_wrapper_resolution (status);
CREATE INDEX IF NOT EXISTS idx_gnews_wrapper_final_domain
    ON gnews_wrapper_resolution (final_domain);
