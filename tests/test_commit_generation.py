import requests
import time
import sys

# Configuration
API_URL = "http://127.0.0.1:80/api/v1"
POLL_INTERVAL = 0.5  # Seconds between checks

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
    },
    {
        "name": "5. 🚩 Mixed Concerns (Faulty Commit)",
        "description": "Changes UI colors AND fixes a critical DB bug. AI should struggle or summarize both.",
        "payload": {
            "diff": """diff --git a/src/styles/main.css b/src/styles/main.css
index 1a2b3c..4d5e6f 100644
--- a/src/styles/main.css
+++ b/src/styles/main.css
@@ -20,1 +20,1 @@ header {
-    background-color: #333;
+    background-color: #ff0000; /* Rebranding to Red */
 }
diff --git a/src/backend/db.py b/src/backend/db.py
index 998877..665544 100644
--- a/src/backend/db.py
+++ b/src/backend/db.py
@@ -50,4 +50,4 @@ def get_user(id):
-    query = f"SELECT * FROM users WHERE id = {id}" # VULNERABLE!
+    query = "SELECT * FROM users WHERE id = %s"    # Fixed SQL Injection""",
            "history": [],
            "config": {
                "project_descriptions": "Legacy web app refactoring.",
                "style": {"convention": "conventional", "useEmojis": False, "language": "en"},
                "rules": []
            }
        }
    },
    {
        "name": "6. 🏴‍☠️ Pirate Mode (Weird Rule)",
        "description": "Forces the AI to speak like a pirate.",
        "payload": {
            "diff": """diff --git a/src/map.js b/src/map.js
index 111..222 100644
--- a/src/map.js
+++ b/src/map.js
@@ -10,1 +10,1 @@
- const treasureLocation = null;
+ const treasureLocation = { x: 42, y: 99 };""",
            "history": [],
            "config": {
                "project_descriptions": "Treasure hunt app.",
                "style": {"convention": "conventional", "useEmojis": True, "language": "en"},
                "rules": [
                    "Write the commit message in Pirate English.",
                    "Start every message with 'ARRR!'",
                    "Use nautical terms."
                ]
            }
        }
    },
    {
        "name": "7. 🌸 Haiku Style (Weird Format)",
        "description": "Forces a 5-7-5 syllable structure.",
        "payload": {
            "diff": """diff --git a/app.py b/app.py
index abc..def 100644
--- a/app.py
+++ b/app.py
@@ -1,1 +1,1 @@
-print("Hello World")
+print("Goodbye World")""",
            "history": [],
            "config": {
                "project_descriptions": "A simple python script.",
                "style": {"convention": "conventional", "useEmojis": False, "language": "en"},
                "rules": [
                    "Ignore standard conventions.",
                    "Write the commit message strictly as a Haiku (5-7-5 syllables).",
                    "Do not use the word 'update'."
                ]
            }
        }
    },
    {
        "name": "8. 🤖 JSON Output (Machine Readable)",
        "description": "Forces the output to be raw JSON.",
        "payload": {
            "diff": """diff --git a/package.json b/package.json
index 111..222 100644
--- a/package.json
+++ b/package.json
@@ -15,1 +15,1 @@
-    "version": "1.0.0"
+    "version": "1.0.1"
""",
            "history": [],
            "config": {
                "project_descriptions": "NPM package.",
                "style": {"convention": "conventional", "useEmojis": False, "language": "en"},
                "rules": [
                    "Output ONLY valid JSON.",
                    "Format: {\"type\": \"...\", \"scope\": \"...\", \"subject\": \"...\"}"
                ]
            }
        }
    },
    {
        "name": "9. ↩️ Revert Commit",
        "description": "Tests logic for reverting changes.",
        "payload": {
            "diff": """diff --git a/src/broken.js b/src/broken.js
index 555..444 100644
--- a/src/broken.js
+++ b/src/broken.js
@@ -1,5 +1,1 @@
-function broken() {
-  throw new Error("Oops");
-}
+function working() {
+  return true;
+}""",
            "history": [],
            "config": {
                "project_descriptions": "NodeJS backend.",
                "style": {"convention": "angular", "useEmojis": True, "language": "en"},
                "rules": ["If this is a revert, explicitly state what is being brought back."]
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