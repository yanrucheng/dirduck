from __future__ import annotations

import subprocess
import sys
from dirduck_transcode.argparser import parse_args
from dirduck_transcode.traversal import run


def main(argv: list[str] | None = None) -> int:
    try:
        config = parse_args(argv)
        return run(config)
    except subprocess.CalledProcessError as error:
        print(f"Command failed with exit code {error.returncode}: {' '.join(error.cmd)}", file=sys.stderr)
        return error.returncode
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted by user.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
