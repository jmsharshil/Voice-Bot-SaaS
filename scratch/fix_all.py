# scratch/fix_all.py

import os

files_to_update = [
    r"c:\Users\AYUSHI PATEL\Eleven_labs\Voice-Bot-SaaS\conversations\consumers.py",
    r"c:\Users\AYUSHI PATEL\Eleven_labs\Voice-Bot-SaaS\conversations\consumers_service2.py"
]

globals_code = """
GLOBAL_SARVAM_CACHE = {}
SARVAM_HTTP_SESSION = None

def get_sarvam_session():
    global SARVAM_HTTP_SESSION
    if SARVAM_HTTP_SESSION is None:
        import requests
        from urllib3.util import Retry
        from requests.adapters import HTTPAdapter
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(pool_connections=10, pool_maxsize=50, max_retries=retries))
        SARVAM_HTTP_SESSION = session
    return SARVAM_HTTP_SESSION
"""

for filepath in files_to_update:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    if "def get_sarvam_session():" not in content:
        # Insert globals right after the imports at the top
        content = content.replace("from django.utils import timezone", globals_code + "\nfrom django.utils import timezone")
        print(f"Added globals to {os.path.basename(filepath)}")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        print(f"Globals already present in {os.path.basename(filepath)}")

print("Fix completed successfully!")
