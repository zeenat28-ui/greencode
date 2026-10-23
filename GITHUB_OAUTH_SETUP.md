# GitHub OAuth Setup

GreenCode uses the local FastAPI backend for GitHub OAuth, repository access,
scans, refactoring, and pull request creation. The local Vite frontend proxies
API requests to FastAPI; this workflow does not require Vercel.

## Local development

1. Create or configure a GitHub OAuth App.
2. Set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in the backend environment
   (for example, the repository-root `.env` file).
3. Set the OAuth App callback URL to `http://localhost:5173/login`.
4. Start the FastAPI backend on port 8000 and the Vite frontend on port 5173.
   The frontend proxies API and GitHub requests to the backend.
5. Open `http://localhost:5173/login` (use `localhost` consistently rather
   than switching between `localhost` and `127.0.0.1`) and sign in with Google
   or another GreenCode account provider.
6. In **Settings → GitHub Integration**, choose **Connect GitHub** and approve
   repository access. Google authenticates the GreenCode account; GitHub OAuth
   separately grants access to repositories. GitHub access tokens stay in the
   current browser session and are not saved by the backend.

## Google sign-in

1. Create a Google OAuth client with application type **Web application**.
2. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in the backend environment.
   Do not put the client secret in the frontend.
3. Add this exact value under **Authorized redirect URIs**:
   `http://localhost:5173/login?provider=google`
4. Start GreenCode and open it using `http://localhost:5173` (not
   `127.0.0.1`). The sign-in uses a server-side authorization-code redirect;
   it does not need a Google Identity Services JavaScript origin.

Google may still require you to add your account as a test user while the
OAuth consent screen is in testing. The app no longer forces a consent prompt
on every sign-in. GreenCode keeps its session with rotating refresh tokens. The refresh
credential survives reloads and transient network/server errors; if an outage
interrupts startup restoration, reload after the backend is available. An
explicit **Log out** revokes it. For security, a refresh token that is revoked
or expires after 30 days without rotation requires signing in again.

Never commit OAuth secrets or copy them into documentation. If a credential was
previously committed or otherwise exposed, revoke it in GitHub and replace it
in every deployment environment.

## Operational limitations

The API health endpoint reports which optional capabilities are active. Dynamic
analysis requires Docker and remains unavailable on deployments without a
supported isolated execution environment. Energy values are estimates unless
the API reports a real hardware measurement source. Missing external provider
credentials should be configured for the integrations you intend to use.
