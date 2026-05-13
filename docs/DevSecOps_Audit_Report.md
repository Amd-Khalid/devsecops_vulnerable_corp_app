# DevSecOps Comprehensive Security Audit & Remediation Report
**Institution:** Habib University 
**Target Application:** Vulnerable Corp App (CorpNet Portal)
**Assessment Type:** White-box DevSecOps Audit (SAST, DAST, SCA, Manual Penetration Testing)

---

## 1. Executive Summary
This report details the DevSecOps security assessment and subsequent remediation of the "Vulnerable Corp App" (CorpNet). The objective of this engagement was to establish a fully automated CI/CD security pipeline, identify critical vulnerabilities through both automated tooling and manual penetration testing, and implement secure coding patches. 

The initial assessment revealed a critical risk posture, including unauthenticated perimeter bypasses (SQL Injection), Business Logic flaws (IDOR), and high-severity Stored XSS. By integrating Software Composition Analysis (SCA), Static Application Security Testing (SAST), and Dynamic Application Security Testing (DAST) into the GitHub Actions deployment pipeline, the team successfully identified and triaged these vulnerabilities. Following the Week 4 remediation phase, all critical and high-severity flaws were successfully patched, effectively securing the application's authentication, authorization, and data validation mechanisms.

---

## 2. Application Overview & Baseline Compliance
CorpNet is a corporate portal web application designed to handle authenticated user sessions, data processing, and internal communications. To ensure a production-ready baseline, the environment was strictly configured to meet the following enterprise requirements:

* **Technology Stack:** Python 3.9, Flask 2.2.2 web framework, and a persistent SQLite3 database.
* **Access Control:** Working Role-Based Access Control (RBAC) separating 'admin' and 'user' roles, coupled with a robust Flask-managed session token mechanism.
* **Data Flow:** Full CRUD (Create, Read, Update, Delete) capabilities integrated into the user dashboard.
* **Deployment Architecture:** The application was fully containerized via Docker and deployed on a distinct network IP/Hostname (avoiding localhost bindings). Furthermore, cryptographic confidentiality was enforced by binding the application to an adhoc SSL context, ensuring all local network traffic was routed over HTTPS.

---

## 3. Architecture & Threat Model
The application’s architecture introduces specific trust boundaries and attack surfaces:
* **External Boundary:** The primary attack surface is the web interface exposed on port 5000. Unauthenticated attackers can interact with the `/login` endpoint.
* **Internal Boundary (Authenticated):** Authenticated standard users have access to the `/dashboard`, `/edit`, and `/delete` endpoints. 
* **Threat Actors:** The primary threat models include external malicious actors attempting to bypass authentication, and internal malicious/compromised users attempting horizontal privilege escalation (IDOR) or vertical privilege escalation (XSS targeting Admins).

---

## 4. DevSecOps Pipeline Integration (CI/CD)
To enforce continuous security, a robust DevSecOps pipeline was engineered using GitHub Actions (`security-pipeline.yml`). The pipeline is triggered automatically on every code push or pull request to the `main` branch.

### 4.1 Software Composition Analysis (SCA) - Syft
* **Implementation:** Anchore Syft was integrated to generate a CycloneDX Software Bill of Materials (SBOM) for complete dependency tracking.
* **Value:** This established a permanent inventory of third-party libraries, ensuring rapid identification of vulnerable components like the outdated `Werkzeug 2.2.2` library.

### 4.2 Static Application Security Testing (SAST) - SonarQube
* **Implementation:** SonarCloud was integrated to statically analyze the Python source code for logic flaws, code smells, and security hotspots before runtime.
* **Value:** SAST successfully caught critical source-code vulnerabilities that runtime tools missed, specifically the hardcoded application secret key and the lack of parameterized queries in the login route.

### 4.3 Dynamic Application Security Testing (DAST) - OWASP ZAP
* **Implementation:** The pipeline builds the Docker container dynamically and utilizes `zaproxy/action-baseline` to launch active web requests against the running HTTPS application at the isolated Docker Bridge IP (`172.17.0.1`).
* **Value:** ZAP audited the application's runtime headers and configuration. While it successfully flagged missing security headers, it accurately demonstrated the limitation of unauthenticated DAST by failing to observe the authenticated dashboard vulnerabilities, justifying the need for manual penetration testing.

---

## 5. Technical Vulnerability Assessment & Exploitation

### 5.1 Chained Exploit: Stored XSS to Administrator Session Hijacking
* **Severity:** High (Estimated CVSS v3.1: 8.7)
* **CVSS Vector String:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:H/A:N`
* **OWASP Top 10 Mapping:** A03:2021 – Injection (Cross-Site Scripting)
* **Discovery Method:** Manual Penetration Testing (Missed by DAST unauthenticated baseline)

**Description & Business Impact:**
The application fails to sanitize user input in the `dashboard.html` template, specifically utilizing the Jinja2 `| safe` filter which bypasses HTML escaping. This allows a standard, low-privileged user to inject malicious JavaScript into the company feed. 

When chained together, this creates a critical business impact: if a high-privileged user (Administrator) logs in to view the corporate feed, the payload executes in their browser, allowing the attacker to silently exfiltrate the Admin's session cookie and completely compromise the administrative account.

**Reproducible Proof of Concept (PoC):**
1. Authenticated as a standard user (`john_doe`), navigate to `/dashboard`.
2. In the "Create a New Post" field, inject the following payload:
   `<h3>URGENT</h3><script>alert('Session Hijacked: ' + document.cookie)</script>`
3. Click "Post". The script is permanently stored in the SQLite database.
4. When the Administrator logs in, the XSS payload triggers automatically upon rendering the dashboard.

![XSS payload entered into the text box](assets/xss-payload.png)
![JavaScript alert pop-up showing execution](assets/xss-alert.png)

---

### 5.2 Business Logic Flaw: Insecure Direct Object Reference (IDOR)
* **Severity:** Medium/High (Estimated CVSS v3.1: 6.5)
* **CVSS Vector String:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:L`
* **OWASP Top 10 Mapping:** A01:2021 – Broken Access Control
* **Discovery Method:** Manual Code Review

**Description & Business Impact:**
The application's post deletion endpoint (`/delete/<int:post_id>`) suffers from an Insecure Direct Object Reference (IDOR) business logic flaw. While the UI only displays the "Delete" button for an author's own posts, the backend routing completely lacks authorization validation. It relies entirely on the URL parameter without checking if the active session owns the requested resource. This allows any authenticated user to maliciously purge the entire corporate database of posts.

**Reproducible Proof of Concept (PoC):**
1. Log in as `john_doe` (Standard User).
2. Observe a post created by `admin` (e.g., Post ID 1). Note there is no UI button to delete it.
3. Manually alter the browser URL to: `https://<hostname>:5000/delete/1`
4. The application processes the request and deletes the Administrator's post, bypassing all intended Role-Based Access Control (RBAC).

---

### 5.3 SQL Injection (Authentication Perimeter Bypass)
* **Severity:** Critical (Estimated CVSS v3.1: 9.8)
* **CVSS Vector String:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`
* **OWASP Top 10 Mapping:** A03:2021 – Injection
* **Discovery Method:** SonarQube (SAST) & Manual Exploitation

**Description & Business Impact:**
Static Application Security Testing (SAST) via SonarCloud identified a blocker-level vulnerability at Line 35 of `app.py`. The login query directly concatenates user input rather than utilizing parameterized queries. Because the username field contains basic regex validation but the password field does not, attackers can inject arbitrary SQL logic into the password parameter to force a true boolean condition, resulting in a full unauthenticated bypass of the perimeter.

**Reproducible Proof of Concept (PoC):**
1. Navigate to `https://<hostname>:5000/login`
2. Enter `admin` in the Username field.
3. Enter `' OR '1'='1` in the Password field.
4. The backend query alters to `SELECT * FROM users WHERE username = 'admin' AND password = '' OR '1'='1'`, authenticating the attacker as the Administrator.

![SonarQube Blocker alert for Line 35](assets/sonarqube-sqli.png)
![Malicious payload entered into the login screen](assets/sqli-bypass.png)

---

### 5.4 Outdated Component & Hardcoded Secrets (Pipeline Findings)
* **Severity:** High
* **OWASP Top 10 Mapping:** A06:2021 (Vulnerable Components) & A07:2021 (Identification Failures)
* **Discovery Method:** Syft (SCA) & SonarQube (SAST)

**Description & Tooling Analysis:**
1. **SCA Findings:** The Syft SBOM generation successfully inventoried the application's dependencies, identifying `Werkzeug==2.2.2` locked within `requirements.txt`. This component is susceptible to a known high-severity Denial of Service (DoS) vulnerability (CVE-2023-25577). 
2. **SAST Findings:** SonarQube identified a critical cryptographic failure: the Flask `app.secret_key` is hardcoded in plaintext within the source code. If the repository is compromised, attackers can locally forge valid cryptographic session cookies to bypass login portals entirely.

![Hardcoded Secret Key in SonarQube](assets/sonarqube-secret.png)

---

### 5.5 Automated Tooling Limitations & False Positives
To ensure an accurate DevSecOps audit, the automated results were manually triaged. The OWASP ZAP (DAST) pipeline step successfully identified the lack of essential security headers (Anti-CSRF Tokens, Content-Security-Policy). 

However, it is vital to note that ZAP produced false negatives for the Stored XSS and IDOR vulnerabilities. This occurred because the GitHub Action pipeline utilizes an *unauthenticated* baseline scan (`zaproxy/action-baseline`). Because the DAST spider could not bypass the login perimeter, it lacked the context to map the authenticated dashboard routes where the business logic flaws and injection points reside. This highlights the absolute necessity of combining automated SAST/SCA tooling with manual penetration testing.

---

## 6. Remediation & Patch Implementation
To transition the application from a vulnerable state to a secure, production-ready release, the following patches were developed and committed to the repository.

### 6.1 Patching SQL Injection (Authentication Security)
To resolve the A03:2021 – Injection vulnerability flagged by SonarQube, the direct string concatenation in the login logic was entirely removed. The backend was refactored to utilize SQLite's native parameterized queries, ensuring user input is treated strictly as data, not executable code.

**Before (Vulnerable `app.py`):**
```python
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
user = conn.execute(query).fetchone()
```

**After (Remediated app.py):**

```Python
query = "SELECT * FROM users WHERE username = ? AND password = ?"
user = conn.execute(query, (username, password)).fetchone()
```

### 6.2 Patching Stored XSS (Input Sanitization)
To neutralize the High-severity cross-site scripting vulnerability, the Jinja2 rendering pipeline was secured. The `| safe` filter, which explicitly instructs the engine to render raw HTML/JavaScript, was stripped from the template. Flask now automatically applies Context-Aware Output Encoding.

**Before (Vulnerable `dashboard.html`):**
```html
{{ post['content'] | safe }} 
```

**After (Remediated `dashboard.html`):**
```html
{{ post['content'] }} 
```

### 6.3 Patching Hardcoded Secrets (Cryptographic Storage)
To resolve the cryptographic blocker identified during the SAST scan, the plaintext `super_secret_key` was removed from the source code. The application was updated to pull the key dynamically from the server's environment variables.

**Before (Vulnerable `app.py`):**
```python
app.secret_key = 'super_secret_key_change_in_production'
```

**After (Remediated `app.py`):**
```python
import os
app.secret_key = os.environ.get('SECRET_KEY', 'default_development_key_if_missing') 
```

### 6.4 Patching IDOR (Authorization Validation)
To enforce strict Role-Based Access Control and fix the business logic flaw in the deletion sequence, a server-side authorization check was added. The endpoint now queries the database to verify if the active session owns the post or possesses 'admin' privileges before executing the `DELETE` command.

**Remediated Route (`app.py`):**
```python
@app.route('/delete/<int:post_id>')
def delete_post(post_id):
    if 'username' not in session:
        return redirect('/login')
        
    conn = get_db_connection()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    
    # Enforce RBAC: Only the author or an admin can delete
    if post and (session.get('username') == post['author'] or session.get('role') == 'admin'):
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
        
    conn.close()
    return redirect('/dashboard')
```

## 7. Conclusion
By integrating automated SCA, SAST, and DAST tooling into the CI/CD pipeline and combining it with rigorous manual penetration testing, the core vulnerabilities within the CorpNet application were successfully identified, exploited, and patched. The resulting remediated application now demonstrates strong defense-in-depth, strictly mitigating the OWASP Top 10 risks identified during the initial baseline phase.