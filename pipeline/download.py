"""Download public scPerturb datasets into data/raw/ and verify checksums.

Zenodo record 13350497 -> download(name) -> data/raw/<file>.h5ad
"""

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

RAW_DIR = Path("data/raw")
ZENODO_URL = "https://zenodo.org/api/records/13350497/files/{file}/content"
CHUNK = 1 << 20  # bytes per read (1 MiB)

DATASETS = {  # name -> (file, md5 published by Zenodo)
    "norman": ("NormanWeissman2019_filtered.h5ad", "c870e6967d91c017d9da827bab183cd6"),
    "replogle": ("ReplogleWeissman2022_K562_essential.h5ad", "d8cba17576d1a8afc0f7d71b79cad0f7"),
}


def md5_of(path: Path) -> str:
    """Compute file MD5.

    In: file path.
    Out: hex digest.
    """
    digest = hashlib.md5()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def download(name: str) -> Path:
    """Download dataset unless a verified copy exists; resume a partial download.

    In: dataset name from DATASETS.
    Out: path of verified file.
    State: writes data/raw/; partial downloads land in *.part, resumed on rerun, removed on mismatch.
    """
    file, expected_md5 = DATASETS[name]
    dest = RAW_DIR / file
    if dest.exists() and md5_of(dest) == expected_md5:
        print(f"{file}: already downloaded, checksum OK")
        return dest

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    have = part.stat().st_size if part.exists() else 0  # bytes kept from an earlier run
    request = urllib.request.Request(ZENODO_URL.format(file=file))
    if have:
        request.add_header("Range", f"bytes={have}-")

    with urllib.request.urlopen(request) as resp:
        if have and resp.status != 206:  # server ignored the range: start over
            have = 0
        digest = hashlib.md5()
        if have:
            with part.open("rb") as f:
                while chunk := f.read(CHUNK):
                    digest.update(chunk)
            print(f"{file}: resuming at {have / 1e6:.0f} MB")
        total = have + int(resp.headers.get("Content-Length", 0))
        done = have
        next_report = done * 100 // total // 10 * 10 + 10 if total else 10  # next progress percent to print
        with part.open("ab" if have else "wb") as out:
            while chunk := resp.read(CHUNK):
                out.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if total and done * 100 >= next_report * total:
                    print(f"{file}: {next_report}% ({done / 1e6:.0f} MB)")
                    next_report += 10

    if digest.hexdigest() != expected_md5:
        part.unlink()
        sys.exit(f"{file}: checksum mismatch, download discarded")
    part.rename(dest)
    print(f"{file}: checksum OK")
    return dest


def main() -> None:
    """Download datasets named on the command line.

    In: one or more dataset names.
    Out: none; prints path and size per dataset.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="+", choices=sorted(DATASETS))
    for name in parser.parse_args().names:
        path = download(name)
        print(f"{path} ({path.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
