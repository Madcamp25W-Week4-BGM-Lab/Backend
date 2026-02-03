import requests
import time
import sys

# Configuration
API_URL = "http://127.0.0.1:80/api/v1"
POLL_INTERVAL = 2  # Seconds between checks

def run_test_scenario(name, payload):
    print(f"\n--- [Scenario: {name}] Sending Request ---")
    
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
                print("\n\n>>> 🤖 LLM Output:")
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

# Define Test Scenarios
scenarios = [
    {
        "name": "1. Standard Fix (Conventional, No Emojis)",
        "payload": {
            "diff": """diff --git a/src/main.py b/src/main.py
index 8a3b1c..9d2f4e 100644
--- a/src/main.py
+++ b/src/main.py
@@ -10,4 +10,4 @@ def calculate_total(price, tax):
-    return price + price * tax
+    return price + (price * tax)""",
            "history": [],
            "config": {
                "project_descriptions": "A standard e-commerce backend.",
                "style": {
                    "convention": "conventional",
                    "useEmojis": False,
                    "language": "en"
                },
                "rules": []
            }
        }
    },
    {
        "name": "2. Feature Add (Gitmoji + Custom Rule)",
        "payload": {
            "diff": """diff --git a/src/auth.py b/src/auth.py
new file mode 100644
index 000000..e69de29
--- /dev/null
+++ b/src/auth.py
@@ -0,0 +1,5 @@
+def login(user, password):
+    # Todo: Implement actual hashing
+    if user == "admin" and password == "1234":
+        return True
+    return False""",
            "history": [],
            "config": {
                "project_descriptions": "Authentication module for the app.",
                "style": {
                    "convention": "gitmoji",
                    "useEmojis": True,
                    "language": "en"
                },
                "rules": [
                    "Mention that this is a temporary mock implementation.",
                    "Include the ticket ID #AUTH-001"
                ]
            }
        }
    },
    {
        "name": "3. Docs Update (Korean Language)",
        "payload": {
            "diff": """diff --git a/README.md b/README.md
index 5f2a1b..2c3d4e 100644
--- a/README.md
+++ b/README.md
@@ -1,3 +1,3 @@
 # SubText
-An AI tool for commits.
+An AI tool for automatic commit message generation and README creation.
""",
            "history": [],
            "config": {
                "project_descriptions": "Documentation for SubText project.",
                "style": {
                    "convention": "conventional",
                    "useEmojis": False,
                    "language": "ko"
                },
                "rules": [
                    "Use a polite tone (honorifics).",
                    "Summarize the change briefly."
                ]
            }
        }
    },
    {
        "name": "4. Security Fix (Angular Style + Strict Rules)",
        "payload": {
            "diff": """diff --git a/src/config.py b/src/config.py
index 112233..445566 100644
--- a/src/config.py
+++ b/src/config.py
@@ -5,2 +5,2 @@ class Settings:
-    SECRET_KEY = "unsafe-hardcoded-key"
+    SECRET_KEY = os.getenv("SECRET_KEY")""",
            "history": [],
            "config": {
                "project_descriptions": "Configuration management.",
                "style": {
                    "convention": "angular",
                    "useEmojis": True,
                    "language": "en"
                },
                "rules": [
                    "Start the subject with 'SECURITY:'",
                    "Do not mention specific variable names in the subject."
                ]
            }
        }
    }
]

if __name__ == "__main__":
    print("🚀 Starting Commit Generation Tests...")
    for scenario in scenarios:
        run_test_scenario(scenario["name"], scenario["payload"])
        time.sleep(1) # Brief pause between tests
    print("\n✅ All tests finished.")