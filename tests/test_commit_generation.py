import requests
import time
import sys

# Configuration
API_URL = "http://127.0.0.1:80/api/v1"
POLL_INTERVAL = 0.5  # Seconds between checks

import subprocess

def get_git_diff(commit_ref="HEAD"):
    """
    Fetches the diff for a specific commit (default: HEAD).
    """
    try:
        # 'git show' with --format="" hides the author/date headers, returning only the diff.
        # --unified=3 gives standard context.
        result = subprocess.check_output(
            ["git", "show", "--format=", "--unified=3", commit_ref],
            stderr=subprocess.STDOUT,
            text=True
        )
        return result.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Git Error: {e.output}")
        return None

def run_test_scenario(name, payload):
    print(f"\n--- [Scenario: {name}] Sending Request ---")
    
    start_time = time.perf_counter()

    # 1. Send the Generation Request
    try:
        response = requests.post(f"{API_URL}/generate-commit", json=payload)
        response.raise_for_status()
        data = response.json()
        task_id = data["task_id"]
        print(f"✅ Request Queued. Task ID: {task_id}")
    except Exception as e:
        print(f"❌ Failed to send request: {e}")
        return

    # 2. Poll for Result
    print("⏳ Polling for result...", end="", flush=True)
    while True:
        try:
            res = requests.get(f"{API_URL}/tasks/{task_id}")
            if res.status_code == 404:
                # Task might not be ready in the lookup yet, or invalid
                time.sleep(POLL_INTERVAL)
                continue
                
            task_data = res.json()
            status = task_data.get("status")

            if status == "completed":
                end_time = time.perf_counter() # End Timer
                duration = end_time - start_time

                print(f"\n\n>>> 🤖 LLM Output (Generated in {duration:.2f}s):")
                print("-" * 40)
                print(task_data.get("commit_message"))
                print("-" * 40)
                break
            elif status == "failed":
                print(f"\n❌ Task Failed: {task_data.get('error')}")
                break
            else:
                # Still pending/processing
                print(".", end="", flush=True)
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\n🛑 Stopped polling.")
            break
        except Exception as e:
            print(f"\n❌ Polling error: {e}")
            break

# Common configs
BASE_STYLE = {"convention": "conventional", "language": "en", "casing": "lower", "max_length": 50}
CONFIG_AUTH = {"project_descriptions": "Auth System", "style": BASE_STYLE, "rules": []}

scenarios = [
    {
        "name": "REAL GIT COMMIT (Last Commit)",
        "payload": {
            # 1. Get the diff dynamically from your local git repo
            "diff": get_git_diff("c8722d575f0e8b90a00a4189d1ff35b4bb3aba59"), 
            
            "history": [],
            "config": {
                "project_descriptions": "My actual project",
                "style": {
                    "convention": "conventional",
                    "language": "en",
                    "max_length": 50
                },
                "rules": []
            }
        }
    },
    # --- BASICS ---
    {
        "name": "Simple Fix (Python)",
        "payload": {
            "diff": "diff --git a/main.py b/main.py\n- x = 1\n+ x = 2",
            "history": [], "config": CONFIG_AUTH
        }
    },
    {
        "name": "New Feature (JS)",
        "payload": {
            "diff": "diff --git a/utils.js b/utils.js\nnew file mode 100644\n+ function add(a, b) { return a + b; }",
            "history": [], "config": CONFIG_AUTH
        }
    },
    {
        "name": "Documentation Update",
        "payload": {
            "diff": "diff --git a/README.md b/README.md\n- # Old Title\n+ # New Title",
            "history": [], "config": CONFIG_AUTH
        }
    },
    {
        "name": "Style Change (CSS)",
        "payload": {
            "diff": "diff --git a/style.css b/style.css\n- color: red;\n+ color: blue;",
            "history": [], "config": CONFIG_AUTH
        }
    },
    {
        "name": "Refactor (Variable Rename)",
        "payload": {
            "diff": "diff --git a/api.py b/api.py\n- def process(data):\n+ def process_request(payload):",
            "history": [], "config": CONFIG_AUTH
        }
    },
    
    # --- CONVENTIONS & STYLES ---
    {
        "name": "Angular Convention",
        "payload": {
            "diff": "diff --git a/src/core.ts b/src/core.ts\n- const MAX_RETRIES = 3;\n+ const MAX_RETRIES = 5;",
            "history": [], 
            "config": {**CONFIG_AUTH, "style": {**BASE_STYLE, "convention": "angular"}}
        }
    },
    {
        "name": "Sentence Casing",
        "payload": {
            "diff": "diff --git a/config.yaml b/config.yaml\n- debug: true\n+ debug: false",
            "history": [], 
            "config": {**CONFIG_AUTH, "style": {**BASE_STYLE, "casing": "sentence"}}
        }
    },
    {
        "name": "Gitmoji Style",
        "payload": {
            "diff": "diff --git a/ui.jsx b/ui.jsx\n- <Button />\n+ <Button variant='primary' />",
            "history": [], 
            "config": {**CONFIG_AUTH, "style": {**BASE_STYLE, "convention": "gitmoji"}}
        }
    },
    
    # --- TICKETS & RULES ---
    {
        "name": "Ticket ID (Append)",
        "payload": {
            "diff": "diff --git a/login.py b/login.py\n# Fixes AUTH-123 login error\n- if not user:\n+ if user is None:",
            "history": [], 
            "config": {
                "project_descriptions": "Auth", 
                "style": {**BASE_STYLE, "ticket_prefix": "AUTH"}, "rules": []
            }
        }
    },
    {
        "name": "Security High Priority",
        "payload": {
            "diff": "diff --git a/secrets.py b/secrets.py\n- key = '12345'\n+ key = os.getenv('KEY')",
            "history": [], 
            "config": {
                "project_descriptions": "Security", 
                "style": BASE_STYLE, 
                "rules": ["Start with 'SECURITY:'"]
            }
        }
    },

    # --- LANGUAGES ---
    {
        "name": "Korean Output",
        "payload": {
            "diff": "diff --git a/msg.txt b/msg.txt\n- Hello\n+ Annyeong",
            "history": [], 
            "config": {**CONFIG_AUTH, "style": {**BASE_STYLE, "language": "ko"}}
        }
    },
    {
        "name": "Japanese Output",
        "payload": {
            "diff": "diff --git a/msg.txt b/msg.txt\n- Hello\n+ Konnichiwa",
            "history": [], 
            "config": {**CONFIG_AUTH, "style": {**BASE_STYLE, "language": "ja"}}
        }
    },

    # --- COMPLEXITY ---
    {
        "name": "Mixed Concerns (Split)",
        "payload": {
            "diff": "diff --git a/ui.css b/ui.css\n- padding: 10px;\n+ padding: 20px;\ndiff --git a/db.py b/db.py\n- query()\n+ secure_query()",
            "history": [], "config": CONFIG_AUTH
        }
    },
    {
        "name": "Dependency Update (Chore)",
        "payload": {
            "diff": "diff --git a/package.json b/package.json\n- \"react\": \"16.0.0\"\n+ \"react\": \"18.0.0\"",
            "history": [], "config": CONFIG_AUTH
        }
    },
    {
        "name": "Breaking Change (!)",
        "payload": {
            "diff": "diff --git a/api.go b/api.go\n- func Get(id int)\n+ func Get(id string) // BREAKING CHANGE",
            "history": [], "config": CONFIG_AUTH
        }
    },
    {
        "name": "Revert Commit",
        "payload": {
            "diff": "diff --git a/app.js b/app.js\n- console.log('debug')\n+ // reverted debug log",
            "history": [], 
            "config": {**CONFIG_AUTH, "rules": ["Mark as Revert"]}
        }
    },
    {
        "name": "Test Update",
        "payload": {
            "diff": "diff --git a/tests/test_login.py b/tests/test_login.py\n- assert True\n+ assert login() == True",
            "history": [], "config": CONFIG_AUTH
        }
    },
    {
        "name": "CI Config",
        "payload": {
            "diff": "diff --git a/.github/workflows/main.yml b/.github/workflows/main.yml\n- runs-on: ubuntu-latest\n+ runs-on: ubuntu-22.04",
            "history": [], "config": CONFIG_AUTH
        }
    },
    {
        "name": "Delete File",
        "payload": {
            "diff": "diff --git a/old_script.sh b/old_script.sh\ndeleted file mode 100644",
            "history": [], "config": CONFIG_AUTH
        }
    },
    {
        "name": "Rename File",
        "payload": {
            "diff": "diff --git a/img.png b/assets/img.png\nrename from img.png\nrename to assets/img.png",
            "history": [], "config": CONFIG_AUTH
        }
    },

    # --- EDGE CASES ---
    {
        "name": "Max Length Constraint",
        "payload": {
            "diff": "diff --git a/long_filename_that_is_very_long.txt b/long.txt\n- content\n+ slightly different content with much meaning",
            "history": [], 
            "config": {**CONFIG_AUTH, "style": {**BASE_STYLE, "max_length": 30}}
        }
    },
    {
        "name": "Typos Fix",
        "payload": {
            "diff": "diff --git a/docs.md b/docs.md\n- Teh end\n+ The end",
            "history": [], "config": CONFIG_AUTH
        }
    },
    {
        "name": "Empty Diff (Trap)",
        "payload": {
            "diff": "",
            "history": [], "config": CONFIG_AUTH
        }
    },
    {
        "name": "Garbage Diff (Trap)",
        "payload": {
            "diff": "afj2309fj 2039fj",
            "history": [], "config": CONFIG_AUTH
        }
    },
    {
        "name": "Multiple Fixes One File",
        "payload": {
            "diff": "diff --git a/app.py b/app.py\n- x=1 # bug1\n+ x=2\n- y=1 # bug2\n+ y=2",
            "history": [], "config": CONFIG_AUTH
        }
    }
]

if __name__ == "__main__":
    print("🚀 Starting Commit Generation Tests...")
    for scenario in scenarios:
        run_test_scenario(scenario["name"], scenario["payload"])
        time.sleep(1) # Brief pause between tests
    print("\n✅ All tests finished.")