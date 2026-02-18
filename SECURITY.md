# Security Policy

## Supported Versions

Only the latest major version of the project is currently supported with security updates.

| Version | Supported |
| :------ | :-------- |
| 2.0.x   | ✅         |
| 1.x.x   | ❌         |

## Reporting a Vulnerability

We take the security of this project seriously. If you discover a security vulnerability, please follow these steps:

1.  **Do NOT open a public issue.** Security vulnerabilities should be reported privately to prevent exploitation before a fix is available.
2.  **Email us** at `security@example.com` (replace with actual contact if available) or reach out directly to the maintainers via private message.
3.  Provide a **detailed description** of the vulnerability, including:
    *   Steps to reproduce.
    *   Potential impact.
    *   Any proof-of-concept code.

## Response Timeline

*   We will acknowledge your report within **48 hours**.
*   We will provide an estimated timeline for the fix within **1 week**.
*   We will notify you once the fix is released.

## Security Best Practices for Users

*   **Never** commit your `.env` file to public repositories.
*   **Rotate** your `ALERT_KEY` and Binance API keys periodically.
*   Use a **strong, random** `ALERT_KEY` for webhook validation.
*   Restrict Binance API keys to your server's **IP address** only.
*   Run the bot behind a reverse proxy (Nginx) with **SSL (HTTPS)** enabled for production use.
