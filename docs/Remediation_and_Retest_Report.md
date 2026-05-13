# Remediation and Re-Test Report
## CorpNet Portal

## Remediation Summary

| ID | Vulnerability | Root Cause | Remediation | Re-Test Method | Status |
|----|---------------|------------|-------------|----------------|--------|
| VULN-01 | SQL Injection (Authentication) | Direct string concatenation in SQL query. | Refactored `app.py` to use SQLite parameterised queries `(?, ?)`. | `test_security_baseline.py:test_sqli_authentication_bypass_fails` | Passed / Fixed |
| VULN-02 | Stored XSS (Company Feed) | Jinja2 `\| safe` filter disabled HTML output encoding. | Removed `\| safe` filter in `dashboard.html` to enforce Context-Aware Autoescaping. | `test_security_baseline.py:test_xss_payload_is_escaped` | Passed / Fixed |
| VULN-03 | IDOR on Post Deletion | Missing authorization check on backend `/delete/<id>` route. | Enforced RBAC check verifying `session['username'] == post['author']` or admin role. | `test_security_baseline.py:test_idor_deletion_fails` | Passed / Fixed |
| VULN-04 | Hardcoded Secrets | Flask secret key stored in plaintext in source code. | Implemented `python-dotenv` to fetch `SECRET_KEY` from environment variables. | SonarCloud Security Hotspot review and manual verification. | Passed / Fixed |
| VULN-05 | Vulnerable Dependency (Werkzeug) | `requirements.txt` locked to vulnerable `Werkzeug==2.2.2` (CVE-2023-25577). | Updated constraint to `Werkzeug>=2.2.3` to apply upstream patches. | Syft SBOM automated analysis in CI/CD pipeline. | Passed / Fixed |

## Re-Test Checklist Before Submission

1. **Unit Testing:** Local `pytest` suite executed and passed successfully validating security controls.
2. **Pipeline Integration:** GitHub Actions DevSecOps Pipeline executed regression tests natively during build phase.
3. **Quality Gate:** SonarCloud analysis reflects 0 Critical/High vulnerabilities.
4. **Evidence Gathering:** Pre-patch exploitation screenshots and post-patch verification screenshots captured in `docs/assets/`.
5. **Dependency Integrity:** Latest `sbom-report.json` artifact verifies `Werkzeug` runs on secure version `2.2.3`.