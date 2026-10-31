"""Reject packaging if the build tree still contains visible mounts."""
import re
import sys
from pathlib import Path


def mounts_under(root, mountinfo):
    root = str(root)
    result = []
    for line in mountinfo.splitlines():
        target = re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), line.split()[4])
        if target == root or target.startswith(root + '/'):
            result.append(target)
    return result


if __name__ == '__main__':
    root = Path(sys.argv[1]).resolve(strict=True)
    remaining = mounts_under(root, Path('/proc/self/mountinfo').read_text())
    if remaining:
        raise SystemExit('Refusing to archive attached build mounts: ' + ', '.join(remaining))
    print('No build mounts visible in packaging namespace')
