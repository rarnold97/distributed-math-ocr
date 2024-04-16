from pathlib import Path
import subprocess
import sys

import mathclips

script_path = Path(__file__).resolve()
mathclips_root = Path(mathclips.__path__[0]).resolve()

def main():
    subprocess.run([sys.executable, "-m", "streamlit", "run",
                    mathclips_root / "front_end"/ "app.py"],
                   stdout = sys.stdout, stderr = sys.stderr, check = True)
    
if __name__ == "__main__":
    main()
