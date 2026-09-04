# Deployment — FRAME (Observer)

> **Note:** FRAME has been consolidated into the AAA state plane (2026-08-26).
> This repository is maintained for historical reference. Active observer
> functionality is now part of AAA.

## Historical Deployment

FRAME previously ran as a standalone observer organ. Its functionality has been
merged into AAA's state plane at port :3001.

## Migration

If you were running FRAME independently:

1. Stop the FRAME container: `docker compose down`
2. Deploy the AAA organ (see AAA DEPLOYMENT.md)
3. Observer drift data is now available at AAA's state plane endpoints

## Historical Architecture

FRAME served as the independent observer in the arifOS federation — the
"Fifth Estate" that reports reality without judgment or execution. Its
state reporting and drift detection capabilities are now integrated into AAA.
