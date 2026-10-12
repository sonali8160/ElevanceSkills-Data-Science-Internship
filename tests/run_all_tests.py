"""Run every test file that is actually included in this repository."""
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = Path(__file__).resolve().parent

checks = [
    ("Task 1", [sys.executable, str(TEST_DIR / "task1_test_cases.py")]),
    ("Task 2", [sys.executable, str(TEST_DIR / "task2_test_cases.py")]),
]
for task_number in range(3, 7):
    checks.append((
        f"Task {task_number}",
        [sys.executable, "-m", "unittest", "discover", "-s", str(TEST_DIR),
         "-p", f"task{task_number}_test_cases.py", "-v"],
    ))

failed = []
for name, command in checks:
    print(f"\n{'=' * 60}\nRunning {name}\n{'=' * 60}", flush=True)
    result = subprocess.run(command, cwd=PROJECT_ROOT)
    if result.returncode:
        failed.append(name)

print(f"\n{'=' * 60}\nFINAL INTERNSHIP TEST REPORT\n{'=' * 60}", flush=True)
if failed:
    print("FAILED:", ", ".join(failed), flush=True)
    sys.exit(1)
print("All six included task test suites passed.", flush=True)
sys.exit(0)
