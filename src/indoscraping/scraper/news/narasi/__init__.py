import os
import subprocess

# Absolute path to src/narasi/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_node_script(script_relative_path="js/main.js"):
    script_path = os.path.join(BASE_DIR, script_relative_path)
    
    try:
        result = subprocess.run(
            ["node", script_path],
            check=True,
            capture_output=True,
            text=True
        )
        print("Node.js Output:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("Node.js Error:", e.stderr)
