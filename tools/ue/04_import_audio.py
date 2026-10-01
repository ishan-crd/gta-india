"""Import synthesised WAVs; loops (A_*) are marked looping."""
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gi_common import *  # noqa

SRC = f"{ASSETS}/audio"
DEST = f"{ROOT}/Audio"


def main():
    ensure_dir(DEST)
    files = sorted(f for f in os.listdir(SRC) if f.endswith(".wav"))
    run_tasks([import_task(os.path.join(SRC, f), DEST) for f in files])
    for f in files:
        name = f[:-4]
        snd = load(f"{DEST}/{name}")
        if not snd:
            warn("audio import failed", name)
            continue
        snd.set_editor_property("looping", name.startswith("A_"))
        log("audio", name)
    save_dir(DEST)
    log("audio done")


main()
