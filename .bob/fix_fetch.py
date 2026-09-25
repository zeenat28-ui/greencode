content = open('ui.py', encoding='utf-8').read()

old = (
    'def fetch_gh_user():\n'
    '    user = st.session_state.get("authenticated_user")\n'
    '    if user and user.get("github_token"):\n'
    '        tok = user["github_token"]\n'
    '    else:\n'
    '        tok = st.session_state.get("github_token") or os.environ.get("GITHUB_TOKEN", "")\n'
    '    return _cached_gh_user(tok)'
)
new = (
    'def fetch_gh_user():\n'
    '    tok = st.session_state.get("github_token") or os.environ.get("GITHUB_TOKEN", "")\n'
    '    return _cached_gh_user(tok)'
)

old2 = (
    'def fetch_gh_repos():\n'
    '    user = st.session_state.get("authenticated_user")\n'
    '    if user and user.get("github_token"):\n'
    '        tok = user["github_token"]\n'
    '    else:\n'
    '        tok = st.session_state.get("github_token") or os.environ.get("GITHUB_TOKEN", "")\n'
    '    return _cached_gh_repos(tok)'
)
new2 = (
    'def fetch_gh_repos():\n'
    '    tok = st.session_state.get("github_token") or os.environ.get("GITHUB_TOKEN", "")\n'
    '    return _cached_gh_repos(tok)'
)

print('old found:', old in content)
content = content.replace(old, new)
print('old2 found:', old2 in content)
content = content.replace(old2, new2)
open('ui.py', 'w', encoding='utf-8').write(content)
print('done')
