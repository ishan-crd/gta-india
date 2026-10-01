"""Import the story dialogue (S_Story_*.wav) into /Game/GTAIndia/Audio/Story."""
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

SRC = f"{ASSETS}/audio/story"
DEST = f"{ROOT}/Audio/Story"
ensure_dir(DEST)
files = sorted(f for f in os.listdir(SRC) if f.endswith(".wav"))
run_tasks([import_task(os.path.join(SRC, f), DEST) for f in files])
ok = sum(1 for f in files if eal.does_asset_exist(f"{DEST}/{f[:-4]}"))
save_dir(DEST)
log("story lines imported", ok, "/", len(files))
