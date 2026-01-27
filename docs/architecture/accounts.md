# Account security

Accounts are separate from the opt-in development owner. The resolver prioritizes authenticated sessions. New accounts start with their own workspace. The development identity remains disabled by default and requires a loopback peer, the development environment and a configured active owner. No account inherits or transfers existing development records.

Passwords are hashed with a random 16-byte salt and scrypt at N=2^17, r=8, p=1. A semaphore caps simultaneous derivations at two. Failed login uses a uniform credential error and performs the same derivation for missing or disabled owners. The in-process budget permits eight credential operations per minute per peer and bounds tracked peers. Production operation will need an edge or shared rate limit with a trusted proxy policy. Duplicate registration can still reveal account existence through its status. [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

Sessions use 256-bit random tokens. Only the SHA-256 token hash is persisted, with a 12-hour absolute expiry and at most ten active tokens per owner. The backend issues an HttpOnly, host-scoped, SameSite=Strict cookie. Outside loopback development it uses the Secure `__Host-` cookie. Authenticated mutations require the exact configured Origin and a session-bound CSRF token held in browser memory. Login and registration require an allowed Origin. Login rotates a supplied session. Password change and session revocation invalidate other sessions, while logout invalidates the current one. [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) · [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)

The browser keeps the session cookie inaccessible to script. It clears its TanStack Query cache on sign-in and sign-out, and never stores passwords, session identifiers or resume drafts in persistent browser storage. Authentication and API responses use `private, no-store`. The trusted frontend must use HTTPS in a hosted environment and set exact allowed origins. Keep development identity disabled outside the local workflow.

## API

| Method | Path under /api/v1/auth | Purpose |
| --- | --- | --- |
| POST | `/register` | Create an account and issue a session |
| POST | `/login` | Verify credentials and rotate session |
| GET / PATCH | `/me` | Read the profile and CSRF token or update the display name |
| POST | `/logout` | Revoke the current session |
| POST | `/revoke-sessions` | Revoke all sessions and issue a fresh one |
| POST | `/password` | Verify the old password, replace it and rotate sessions |
| DELETE | `/me` | Verify password and remove all account-owned data |

Removal clears same-owner copy lineage and deletes owned resumes, checkpoints, exports, jobs, analyses and sessions in one transaction. It does not affect other owners or local developer data. SQLite storage is unencrypted. Email verification, password reset delivery, MFA, production load tests and reverse-proxy configuration remain open.
