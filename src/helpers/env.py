import pathlib

from decouple import AutoConfig

THIS_DIR = pathlib.Path(__file__).resolve().parent
BASE_DIR = THIS_DIR.parent
REPO_DIR = BASE_DIR.parent

# AutoConfig searches for .env files in BASE_DIR → REPO_DIR → home dir,
# and always falls back to os.environ — so Railway-injected vars work too.
config = AutoConfig(search_path=str(BASE_DIR))