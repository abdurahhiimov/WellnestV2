WEARABLES_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_date TEXT NOT NULL,
    metric_type TEXT NOT NULL,
    value REAL,
    value_text TEXT,
    unit TEXT,
    source TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(metric_date, metric_type, source)
);

CREATE TABLE IF NOT EXISTS integration_tokens (
    provider TEXT PRIMARY KEY,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TEXT,
    scope TEXT,
    metadata_json TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    records_added INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
"""
