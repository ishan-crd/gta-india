"""Import the crowd's Hindi voice clips."""
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

SRC = f"{ASSETS}/audio/voice"
DEST = f"{ROOT}/Audio/Voice"
ensure_dir(DEST)
files = sorted(f for f in os.listdir(SRC) if f.endswith(".wav"))
run_tasks([import_task(os.path.join(SRC, f), DEST) for f in files])
ok = sum(1 for f in files if eal.does_asset_exist(f"{DEST}/{f[:-4]}"))
save_dir(DEST)
log("voices imported", ok, "/", len(files))
