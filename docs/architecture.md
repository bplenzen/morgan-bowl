# Architecture Notes

This document will collect diagrams, sequencing details, and assumptions as the Morgan Bowl DataOps stack evolves.

## Components
- **Ingestion**: Python clients pulling Sleeper league, roster, matchup, and transaction data.
- **Processing**: DuckDB as landing zone with dbt transformations to derive marts.
- **Automation**: Prefect flows and GitLab CI orchestrating ingestion + dbt steps.
- **Analytics**: Lightdash/Metabase for dashboards; notebooks for exploration.
- **Observability**: Elementary for dbt health, structured logs, and alerting hooks.

Add architecture diagrams (Excalidraw/diagrams.net exports) in this directory as the design matures.
