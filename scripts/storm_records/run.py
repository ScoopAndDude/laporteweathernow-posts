#!/usr/bin/env python3
"""Storm records test entry point: python3 scripts/storm_records/run.py [probe|build|auto]."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

mode = (sys.argv[1] if len(sys.argv) > 1 else "auto").strip().lower()
if mode in ("probe", "auto") and not os.path.exists(os.path.join(HERE, "build.py")):
    import probe
    probe.main()
elif mode == "probe":
    import probe
    probe.main()
else:
    import build
    build.main()
