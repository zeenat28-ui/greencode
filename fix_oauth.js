const fs = require("fs");
let src = fs.readFileSync("api/index.py", "utf8");

// Find and replace the fake github oauth handler
const fakeStart = src.indexOf('if parsed_path in ("/api/auth/github/oauth"');
const fakeEnd = src.indexOf('\n        if parsed_path', fakeStart + 10);

if (fakeStart === -1) {
  console.log("ERROR: Could not find github oauth handler");
  process.exit(1);
}

console.log("Found fake handler at:", fakeStart, "to", fakeEnd);
console.log("Fake code snippet:", src.slice(fakeStart, fakeStart+100));

const realHandler = `if parsed_path in ("/api/auth/github/oauth", "/auth/github/oauth"):
            code = body.get("code", "")
            redirect_uri = body.get("redirect_uri", "")
            cid = os.environ.get("GITHUB_CLIENT_ID", "").strip()
            csec = os.environ.get("GITHUB_CLIENT_SECRET", "").strip()
            if not cid or not csec:
                self._send_json({"success": False, "detail": "GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET not set on server"}, 400)
                return
            try:
                import urllib.request as _ur, urllib.parse as _up
                data = _up.urlencode({"client_id": cid, "client_secret": csec, "code": code, "redirect_uri": redirect_uri}).encode()
                req = _ur.Request("https://github.com/login/oauth/access_token", data=data,
                    headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
                tok = json.loads(_ur.urlopen(req, timeout=10).read())
                at = tok.get("access_token")
                if not at:
                    self._send_json({"success": False, "detail": "GitHub token exchange failed: " + str(tok.get("error_description", tok))}, 400)
                    return
                r2 = _ur.Request("https://api.github.com/user",
                    headers={"Authorization": "token " + at, "Accept": "application/vnd.github.v3+json"})
                p = json.loads(_ur.urlopen(r2, timeout=10).read())
                login = p.get("login", "user")
                email = p.get("email") or login + "@users.noreply.github.com"
                full_name = p.get("name") or login
                avatar = p.get("avatar_url", "")
                token = _make_jwt(1, login, email)
                u = {"id": 1, "email": email, "username": login, "full_name": full_name,
                     "role": "developer", "org_id": 1, "avatar_url": avatar}
                self._send_json({"success": True, "access_token": token, "refresh_token": token,
                    "token_type": "bearer", "user": u, "github_token": at,
                    "message": "Authenticated as @" + login})
            except Exception as e:
                self._send_json({"success": False, "detail": str(e)}, 400)
            return
`;

src = src.slice(0, fakeStart) + realHandler + src.slice(fakeEnd);

// Also add _make_jwt if missing
if (!src.includes("def _make_jwt")) {
  const jwtHelper = `
def _make_jwt(uid, username, email):
    import hmac, hashlib, base64, datetime
    secret = os.environ.get("JWT_SECRET", "greencode-secret").encode()
    now = int(datetime.datetime.utcnow().timestamp())
    hdr = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=")
    pay = base64.urlsafe_b64encode(json.dumps({"sub": str(uid), "email": email, "username": username,
        "role": "developer", "org_id": 1, "iat": now, "exp": now + 86400}).encode()).rstrip(b"=")
    msg = hdr + b"." + pay
    sig = base64.urlsafe_b64encode(hmac.new(secret, msg, hashlib.sha256).digest()).rstrip(b"=")
    return (msg + b"." + sig).decode()

`;
  src = src.replace("\nclass handler(BaseHTTPRequestHandler):", jwtHelper + "\nclass handler(BaseHTTPRequestHandler):");
  console.log("Added _make_jwt helper");
}

fs.writeFileSync("api/index.py", src, {encoding: "utf8"});
console.log("Done. Size:", src.length);
