from pathlib import Path
import subprocess
import sys

import mathclips

script_path = Path(__file__).parent.resolve()

def main():
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"],
                   cwd = script_path, stdout = sys.stdout, stderr = sys.stderr, check = True)
    
if __name__ == "__main__":
    main()
