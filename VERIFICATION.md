# Verification dashboard

Run the repository evidence console with no external dependencies:

```bash
python3 verification_dashboard.py --open
```

The dashboard runs the supplied dataset, recomputes the published savings ranges, executes synthetic fixtures for the documented data-corruption cases, checks agent routing and financial guardrails, and separates repository evidence from checks that require a site visit.

Other modes:

```bash
python3 verification_dashboard.py --json
python3 verification_dashboard.py --export verification/index.html
```

## Status meanings

- **Verified:** executable evidence passed.
- **Partial:** documented or implemented, but not fully automated.
- **Failed:** executable verification failed.
- **Field check:** cannot be proven from repository evidence alone.

The score excludes physical and external validation items. A green score therefore means the repository evidence is internally reproducible; it does not claim realized savings, physical equipment attribution, or a guaranteed utility refund.
