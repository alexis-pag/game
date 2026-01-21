import subprocess
import sys

REQUIRED_PACKAGES = [
    "pygame",
    "requests"
]

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

for pkg in REQUIRED_PACKAGES:
    install(pkg)
print("All required packages have been installed.")