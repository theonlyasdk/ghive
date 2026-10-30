import sys, time, ctypes, os
from ctypes import wintypes
from PIL import ImageGrab

ROOT = r"C:\Users\User\Documents\GitHub\ghive"
sys.path.insert(0, ROOT + r"\src")
os.chdir(ROOT)

MOCK_REPOS = [
    {"name":"hello-world","nameWithOwner":"octocat/hello-world","description":"My first repository on GitHub","isPrivate":False,"isFork":False,"stargazerCount":128,"forkCount":42,"updatedAt":"2026-10-28T14:22:00Z","url":"https://github.com/octocat/hello-world"},
    {"name":"Spoon-Knife","nameWithOwner":"octocat/Spoon-Knife","description":"This repo is for demonstration purposes only.","isPrivate":False,"isFork":True,"stargazerCount":1500,"forkCount":13000,"updatedAt":"2026-10-25T09:10:00Z","url":"https://github.com/octocat/Spoon-Knife"},
    {"name":"octocat.github.io","nameWithOwner":"octocat/octocat.github.io","description":"Personal website","isPrivate":False,"isFork":False,"stargazerCount":45,"forkCount":12,"updatedAt":"2026-10-22T18:05:00Z","url":"https://github.com/octocat/octocat.github.io"},
    {"name":"private-notes","nameWithOwner":"octocat/private-notes","description":"Internal notes and drafts","isPrivate":True,"isFork":False,"stargazerCount":3,"forkCount":1,"updatedAt":"2026-10-30T11:45:00Z","url":"https://github.com/octocat/private-notes"},
    {"name":"git-consortium","nameWithOwner":"octocat/git-consortium","description":"Git documentation and consortium","isPrivate":False,"isFork":False,"stargazerCount":320,"forkCount":88,"updatedAt":"2026-10-19T07:30:00Z","url":"https://github.com/octocat/git-consortium"},
    {"name":"linguist","nameWithOwner":"octocat/linguist","description":"Language Savant","isPrivate":False,"isFork":True,"stargazerCount":7,"forkCount":2,"updatedAt":"2026-10-15T16:20:00Z","url":"https://github.com/octocat/linguist"},
]

MOCK_ISSUES = [
    {"number":42,"title":"Add dark mode support","state":"OPEN","author":{"login":"octocat"},"labels":[{"name":"enhancement"}],"createdAt":"2026-10-20T10:00:00Z","updatedAt":"2026-10-28T14:22:00Z","url":"https://github.com/octocat/hello-world/issues/42"},
    {"number":39,"title":"Fix login redirect loop","state":"OPEN","author":{"login":"monalisa"},"labels":[{"name":"bug"},{"name":"priority"}],"createdAt":"2026-10-18T09:00:00Z","updatedAt":"2026-10-27T12:10:00Z","url":"https://github.com/octocat/hello-world/issues/39"},
    {"number":37,"title":"Update README with screenshots","state":"OPEN","author":{"login":"hubot"},"labels":[{"name":"documentation"}],"createdAt":"2026-10-15T08:00:00Z","updatedAt":"2026-10-26T10:30:00Z","url":"https://github.com/octocat/hello-world/issues/37"},
    {"number":33,"title":"Crash on empty repository list","state":"CLOSED","author":{"login":"octocat"},"labels":[{"name":"bug"}],"createdAt":"2026-10-10T11:00:00Z","updatedAt":"2026-10-24T09:15:00Z","url":"https://github.com/octocat/hello-world/issues/33"},
    {"number":28,"title":"Add export to CSV feature","state":"OPEN","author":{"login":"defunkt"},"labels":[],"createdAt":"2026-10-05T13:00:00Z","updatedAt":"2026-10-23T15:40:00Z","url":"https://github.com/octocat/hello-world/issues/28"},
    {"number":25,"title":"Improve error messages","state":"CLOSED","author":{"login":"monalisa"},"labels":[{"name":"good first issue"}],"createdAt":"2026-10-01T07:00:00Z","updatedAt":"2026-10-21T11:20:00Z","url":"https://github.com/octocat/hello-world/issues/25"},
    {"number":21,"title":"Support multiple accounts","state":"OPEN","author":{"login":"octocat"},"labels":[{"name":"enhancement"}],"createdAt":"2026-09-28T12:00:00Z","updatedAt":"2026-10-20T08:50:00Z","url":"https://github.com/octocat/hello-world/issues/21"},
    {"number":17,"title":"Keyboard shortcuts documentation","state":"OPEN","author":{"login":"hubot"},"labels":[{"name":"docs"}],"createdAt":"2026-09-20T14:00:00Z","updatedAt":"2026-10-18T17:05:00Z","url":"https://github.com/octocat/hello-world/issues/17"},
]

MOCK_PRS = [
    {"number":15,"title":"feat: add release management dialog","state":"OPEN","author":{"login":"octocat"},"headRefName":"feature/releases","baseRefName":"main","isDraft":False,"createdAt":"2026-10-27T10:00:00Z","updatedAt":"2026-10-29T16:00:00Z","url":"https://github.com/octocat/hello-world/pull/15"},
    {"number":14,"title":"fix: handle missing gh binary gracefully","state":"OPEN","author":{"login":"monalisa"},"headRefName":"fix/gh-path","baseRefName":"main","isDraft":True,"createdAt":"2026-10-24T09:00:00Z","updatedAt":"2026-10-28T11:30:00Z","url":"https://github.com/octocat/hello-world/pull/14"},
    {"number":12,"title":"docs: add contributing guide","state":"MERGED","author":{"login":"hubot"},"headRefName":"docs/contrib","baseRefName":"main","isDraft":False,"createdAt":"2026-10-20T08:00:00Z","updatedAt":"2026-10-25T14:20:00Z","url":"https://github.com/octocat/hello-world/pull/12"},
    {"number":10,"title":"refactor: async runner improvements","state":"OPEN","author":{"login":"defunkt"},"headRefName":"refactor/async","baseRefName":"develop","isDraft":False,"createdAt":"2026-10-18T12:00:00Z","updatedAt":"2026-10-26T09:10:00Z","url":"https://github.com/octocat/hello-world/pull/10"},
    {"number":8,"title":"feat: gist file editing","state":"CLOSED","author":{"login":"octocat"},"headRefName":"feature/gists","baseRefName":"main","isDraft":False,"createdAt":"2026-10-12T07:00:00Z","updatedAt":"2026-10-22T18:45:00Z","url":"https://github.com/octocat/hello-world/pull/8"},
    {"number":5,"title":"chore: bump dependencies","state":"MERGED","author":{"login":"monalisa"},"headRefName":"chore/deps","baseRefName":"main","isDraft":False,"createdAt":"2026-10-05T10:00:00Z","updatedAt":"2026-10-19T13:30:00Z","url":"https://github.com/octocat/hello-world/pull/5"},
]

MOCK_RUNS = [
    {"databaseId":123456,"name":"CI","status":"completed","conclusion":"success","workflowName":"Build and Test","headBranch":"main","event":"push","createdAt":"2026-10-30T08:00:00Z","url":"https://github.com/octocat/hello-world/actions/runs/123456"},
    {"databaseId":123455,"name":"Lint","status":"completed","conclusion":"failure","workflowName":"Lint","headBranch":"feature/releases","event":"pull_request","createdAt":"2026-10-29T19:00:00Z","url":"https://github.com/octocat/hello-world/actions/runs/123455"},
    {"databaseId":123454,"name":"Deploy","status":"in_progress","conclusion":None,"workflowName":"Deploy to Pages","headBranch":"main","event":"workflow_dispatch","createdAt":"2026-10-30T09:30:00Z","url":"https://github.com/octocat/hello-world/actions/runs/123454"},
    {"databaseId":123453,"name":"CI","status":"completed","conclusion":"success","workflowName":"Build and Test","headBranch":"develop","event":"push","createdAt":"2026-10-28T14:00:00Z","url":"https://github.com/octocat/hello-world/actions/runs/123453"},
    {"databaseId":123452,"name":"Nightly","status":"completed","conclusion":"cancelled","workflowName":"Nightly","headBranch":"main","event":"schedule","createdAt":"2026-10-27T00:00:00Z","url":"https://github.com/octocat/hello-world/actions/runs/123452"},
    {"databaseId":123451,"name":"CI","status":"queued","conclusion":None,"workflowName":"Build and Test","headBranch":"feature/gists","event":"pull_request","createdAt":"2026-10-30T10:15:00Z","url":"https://github.com/octocat/hello-world/actions/runs/123451"},
]

MOCK_GISTS = [
    {"id":"a1b2c3d4e5f6a7b8c9d0","description":"Python hello world snippet","public":True,"files":["hello.py"],"file_count":1,"created_at":"2026-10-28T10:00:00Z","updated_at":"2026-10-29T12:00:00Z","url":"https://gist.github.com/a1b2c3d4e5f6a7b8c9d0"},
    {"id":"b2c3d4e5f6a7b8c9d0e1","description":"Useful git aliases","public":True,"files":[".gitconfig","aliases.sh"],"file_count":2,"created_at":"2026-10-25T09:00:00Z","updated_at":"2026-10-27T15:30:00Z","url":"https://gist.github.com/b2c3d4e5f6a7b8c9d0e1"},
    {"id":"c3d4e5f6a7b8c9d0e1f2","description":"Secret API token template","public":False,"files":["config.json"],"file_count":1,"created_at":"2026-10-22T11:00:00Z","updated_at":"2026-10-26T08:45:00Z","url":"https://gist.github.com/c3d4e5f6a7b8c9d0e1f2"},
    {"id":"d4e5f6a7b8c9d0e1f2a3","description":"Markdown cheatsheet","public":True,"files":["cheatsheet.md"],"file_count":1,"created_at":"2026-10-18T14:00:00Z","updated_at":"2026-10-24T10:10:00Z","url":"https://gist.github.com/d4e5f6a7b8c9d0e1f2a3"},
    {"id":"e5f6a7b8c9d0e1f2a3b4","description":"Tkinter layout helpers","public":False,"files":["layout.py","README.md"],"file_count":2,"created_at":"2026-10-15T08:00:00Z","updated_at":"2026-10-23T17:20:00Z","url":"https://gist.github.com/e5f6a7b8c9d0e1f2a3b4"},
    {"id":"f6a7b8c9d0e1f2a3b4c5","description":"Docker compose example","public":True,"files":["docker-compose.yml"],"file_count":1,"created_at":"2026-10-10T16:00:00Z","updated_at":"2026-10-20T09:00:00Z","url":"https://gist.github.com/f6a7b8c9d0e1f2a3b4c5"},
]

from ui import MainWindow
app = MainWindow("gh")
app.root.attributes('-topmost', True)
app.root.lift()
app.root.focus_force()

app.gh_manager.auth.get_status = lambda: {"logged_in": True, "user": "octocat", "host": "github.com", "active": True, "scopes": ["repo","gist","workflow"], "raw": ""}
app.gh_manager.repos.list_repos = lambda **kw: [r for r in MOCK_REPOS]
app.gh_manager.issues.list_issues = lambda **kw: [i for i in MOCK_ISSUES]
app.gh_manager.prs.list_prs = lambda **kw: [p for p in MOCK_PRS]
app.gh_manager.runs.list_runs = lambda **kw: [r for r in MOCK_RUNS]
app.gh_manager.gists.list_gists = lambda **kw: [g for g in MOCK_GISTS]

def pump(ms):
    end = time.time() + ms/1000.0
    while time.time() < end:
        try:
            app.root.update()
            app.root.update_idletasks()
        except Exception:
            break
        time.sleep(0.04)

def hwnd_rect():
    hwnd = app.root.winfo_id()
    rect = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect

def capture(path):
    pump(300)
    r = hwnd_rect()
    img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
    img.save(path)
    print("saved", path, flush=True)

pump(1500)
capture(os.path.join(ROOT, "screenshots", "repositories.png"))

app._on_active_repo_changed("octocat/hello-world")
pump(1500)

for tabname, fname in [("Issues","issues.png"),("Pull Requests","pull_requests.png"),("Actions","actions.png"),("Gists","gists.png")]:
    for i in range(app.notebook.index("end")):
        if app.notebook.tab(i, "text") == tabname:
            app.notebook.select(i)
            break
    pump(1200)
    capture(os.path.join(ROOT, "screenshots", fname))

app.root.destroy()
print("DONE", flush=True)
