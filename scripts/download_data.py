"""Download the raw LOLA / illumination / Diviner files into data/raw/ - safely.

Python standard library only (no pip installs). Run from the repo root:

    .venv\\Scripts\\python scripts\\download_data.py              (Windows)
    python3 scripts/download_data.py                              (Mac/Linux)

What it does for every file:
  * asks the server how big the file should be, and refuses web pages (HTML);
  * NASA PGDA throttles each connection to ~15 KB/s, so big files are fetched as
    several byte ranges in parallel (--connections, default 8): ~10x faster;
  * downloads to NAME.part (or NAME.parts/ when parallel), resumes if interrupted,
    retries on network errors;
  * checks the final size and (for .TIF) that it really is a TIFF image;
  * only then renames it to its real name, and records the URL in data/raw/SOURCES.txt.
A file that is already present AND valid is skipped; a bad one is replaced.

Options:
  --only illum dem diviner     download just those groups (default: all)
  --dem-res 80 40 20           DEM resolution(s) in m/px (default: 40, 685 MB, what
                               config.yaml uses). 20 m is 2.6 GB: hours even in parallel.
  --connections N              parallel connections per large file (default 8).
  --verify                     don't download; just check what is already on disk.
"""
from __future__ import annotations

import argparse
import math
import threading
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import http.client
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
UA = "Mozilla/5.0 (Optima-luna hackathon downloader)"
CHUNK = 1024 * 1024
RETRIES = 10
CONNECTIONS = 8
PARALLEL_MIN_BYTES = 20 * 1024 * 1024   # smaller files: one connection is fine
TIFF_MAGIC = (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")  # TIFF + BigTIFF

PGDA_ILLUM = "https://pgda.gsfc.nasa.gov/data/MoonIllumination/"
PGDA_DEM = "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/"
PDS_PRP = "https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_prp/"

# (group, folder, filename, base url, exact_bytes or None, min_bytes)
# Sizes for the DEM are the rounded sizes printed on the PGDA page (min_bytes is ~80% of that);
# Diviner sizes are exact from the PDS directory listing.
FILES = [
    ("illum", "lola_illum", "AVGVISIB_75S_120M_201608.TIF", PGDA_ILLUM, None, 100_000),         # -> illum_frac
    ("illum", "lola_illum", "AVGVISIB_75S_120M_201608_EARTH.TIF", PGDA_ILLUM, None, 100_000),   # -> earth_los_frac
    ("illum", "lola_illum", "LPSR_75S_120M_201608.TIF", PGDA_ILLUM, None, 100_000),             # -> psr_frac
    ("dem", "lola", "LDEM_80S_80MPP_ADJ.TIF", PGDA_DEM, None, 150_000_000),   # 181 MB
    ("dem", "lola", "LDEM_80S_40MPP_ADJ.TIF", PGDA_DEM, None, 550_000_000),   # 685 MB
    ("dem", "lola", "LDEM_80S_20MPP_ADJ.TIF", PGDA_DEM, None, 2_000_000_000), # 2.6 GB
    ("diviner", "diviner", "dlre_prp_south.tab", PDS_PRP, 604_800_210, 604_800_210),
    ("diviner", "diviner", "dlre_prp_south.lbl", PDS_PRP, 2_167, 2_167),
    ("diviner", "diviner", "dlre_prp_south.xml", PDS_PRP, 14_561, 14_561),
]


class BadDownload(Exception):
    pass


def human(n: float) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:,.1f} {u}" if u != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} GB"


def looks_like_html(head: bytes) -> bool:
    h = head[:2048].lower()
    return b"<html" in h or b"<!doctype html" in h or b"<head" in h or b"<body" in h


def validate(path: Path, exact: int | None, min_bytes: int, server_total: int | None = None) -> str | None:
    """Return None if the file is good, otherwise a short reason string."""
    if not path.exists():
        return "missing"
    size = path.stat().st_size
    with open(path, "rb") as f:
        head = f.read(2048)
    if looks_like_html(head):
        return f"it is a web page, not data ({human(size)})"
    if path.suffix.lower() in (".tif", ".tiff") and head[:4] not in TIFF_MAGIC:
        return "not a valid TIFF image"
    if exact is not None and size != exact:
        return f"size {size:,} B but expected {exact:,} B"
    if server_total is not None and size != server_total:
        return f"size {size:,} B but server says {server_total:,} B"
    if size < min_bytes:
        return f"only {human(size)} - too small (expected at least {human(min_bytes)})"
    return None


def probe(url: str) -> tuple[int | None, str, bool]:
    """(total size, content-type, server supports resume) without downloading the body."""
    req = urllib.request.Request(url, headers={"Range": "bytes=0-0", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        ctype = r.headers.get("Content-Type", "")
        cr = r.headers.get("Content-Range")
        if cr and "/" in cr and cr.split("/")[-1].isdigit():
            total = int(cr.split("/")[-1])
        else:
            cl = r.headers.get("Content-Length")
            total = int(cl) if cl and cl.isdigit() else None
        return total, ctype, r.status == 206


def fetch_parallel(url: str, part: Path, total: int, n: int, retries: int = RETRIES) -> None:
    """Download `url` as n byte ranges at once into part.parent/NAME.parts/, then join into `part`.
    Each range resumes from what is already on disk, so re-running continues."""
    pdir = part.with_name(part.name + "s")          # NAME.part -> NAME.parts/
    pdir.mkdir(parents=True, exist_ok=True)
    size = math.ceil(total / n)
    ranges = [(i, i * size, min(total, (i + 1) * size) - 1) for i in range(n)]
    done = threading.Event()

    def worker(rng):
        i, start, end = rng
        p, want = pdir / str(i), end - start + 1
        for attempt in range(1, retries * 10 + 1):      # throttled server: be patient
            have = p.stat().st_size if p.exists() else 0
            if have >= want:
                return
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": f"bytes={start + have}-{end}"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    if r.status != 206:
                        raise BadDownload("server ignored the byte-range request")
                    with open(p, "ab") as f:
                        while buf := r.read(CHUNK):
                            f.write(buf)
            except (urllib.error.URLError, http.client.HTTPException, OSError, TimeoutError):
                time.sleep(min(3 * attempt, 30))
        raise BadDownload(f"range {i} gave up. Run the script again to resume.")

    def progress():
        t0 = time.time()
        first = sum(q.stat().st_size for q in pdir.iterdir())
        while not done.wait(5):
            have = sum(q.stat().st_size for q in pdir.iterdir())
            speed = (have - first) / max(time.time() - t0, 1e-6)
            eta = f", ETA {(total - have) / speed / 60:.0f} min" if speed > 0 else ""
            print(f"\r  {human(have)} / {human(total)} {100 * have / total:5.1f}% "
                  f"{human(speed)}/s over {n} connections{eta}   ", end="", flush=True)

    threading.Thread(target=progress, daemon=True).start()
    try:
        with ThreadPoolExecutor(n) as ex:
            list(ex.map(worker, ranges))
    finally:
        done.set()
        print()
    with open(part, "wb") as out:
        for i, _, _ in ranges:
            with open(pdir / str(i), "rb") as f:
                while buf := f.read(CHUNK):
                    out.write(buf)
    if part.stat().st_size == total:
        for q in pdir.iterdir():
            q.unlink()
        pdir.rmdir()


def fetch(url: str, dest: Path, exact: int | None, min_bytes: int, retries: int = RETRIES, backoff: float = 3.0,
          connections: int = CONNECTIONS) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    total, ctype, can_resume = probe(url)
    if "html" in ctype.lower():
        raise BadDownload(f"server answered with a web page ({ctype}) - the URL is wrong or blocked")
    if total is not None and total < min_bytes:
        raise BadDownload(f"server reports only {human(total)} for this file (expected at least {human(min_bytes)})")

    if dest.exists():
        why = validate(dest, exact, min_bytes, total)
        if why is None:
            print(f"  already complete ({human(dest.stat().st_size)}) - skipping")
            return
        print(f"  existing file is bad ({why}) - replacing it")
        dest.unlink()

    part = dest.with_name(dest.name + ".part")
    if can_resume and total and total >= PARALLEL_MIN_BYTES and connections > 1:
        fetch_parallel(url, part, total, connections, retries)
        why = validate(part, exact, min_bytes, total)
        if why:
            part.unlink(missing_ok=True)
            raise BadDownload(why)
        os.replace(part, dest)
        return
    last_err = None
    for attempt in range(1, retries + 1):
        have = part.stat().st_size if part.exists() else 0
        if total is not None and have > total:
            part.unlink(); have = 0
        if total is not None and have == total:
            break
        headers = {"User-Agent": UA}
        if have and can_resume:
            headers["Range"] = f"bytes={have}-"
        elif have:
            part.unlink(); have = 0
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                if have and r.status != 206:      # server ignored the resume request
                    have = 0
                mode = "ab" if have else "wb"
                t0, got = time.time(), 0
                with open(part, mode) as f:
                    while True:
                        buf = r.read(CHUNK)
                        if not buf:
                            break
                        f.write(buf); got += len(buf)
                        done = have + got
                        speed = got / max(time.time() - t0, 1e-6)
                        pct = f"{100 * done / total:5.1f}%" if total else ""
                        print(f"\r  {human(done)} / {human(total) if total else '?'} {pct} {human(speed)}/s   ", end="", flush=True)
            print()
            if total is None or part.stat().st_size >= total:
                break
            last_err = "connection ended early"
        except (urllib.error.URLError, http.client.HTTPException, OSError, TimeoutError) as e:
            print()
            last_err = f"{type(e).__name__}: {e}"
        wait = min(backoff * attempt, 30)
        print(f"  interrupted ({last_err}); retry {attempt}/{retries} in {wait:.0f}s (will resume)...")
        time.sleep(wait)
    else:
        raise BadDownload(f"gave up after {retries} tries ({last_err}). Run the script again to resume.")

    why = validate(part, exact, min_bytes, total)
    if why:
        part.unlink(missing_ok=True)
        raise BadDownload(why)
    os.replace(part, dest)


def log_source(path: Path, url: str) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    with open(RAW / "SOURCES.txt", "a", encoding="utf-8") as f:
        f.write(f"{dt.date.today()} | {path.relative_to(ROOT).as_posix()} | {path.stat().st_size} bytes | {url}\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="+", choices=["illum", "dem", "diviner"])
    ap.add_argument("--dem-res", nargs="+", choices=["80", "40", "20"], default=["40"])
    ap.add_argument("--connections", type=int, default=CONNECTIONS)
    ap.add_argument("--verify", action="store_true", help="only check files already on disk")
    a = ap.parse_args(argv)

    groups = set(a.only or ["illum", "dem", "diviner"])
    todo = [f for f in FILES if f[0] in groups and (f[0] != "dem" or any(f"_{r}MPP_" in f[2] for r in a.dem_res))]
    failed, ok = [], []
    print(f"Saving into {RAW}\n")
    for group, folder, name, base, exact, min_bytes in todo:
        dest, url = RAW / folder / name, base + name
        print(f"[{group}] {name}")
        try:
            if a.verify:
                why = validate(dest, exact, min_bytes)
                print("  OK" if why is None else f"  PROBLEM: {why}")
                (ok if why is None else failed).append(name)
                continue
            fetch(url, dest, exact, min_bytes, connections=a.connections)
            log_source(dest, url)
            ok.append(name)
            print(f"  OK  {human(dest.stat().st_size)}")
        except (BadDownload, urllib.error.URLError, OSError) as e:
            print(f"  FAILED: {e}")
            failed.append(name)
    print("\n=== SUMMARY ===")
    print(f"OK ({len(ok)}): " + (", ".join(ok) or "-"))
    print(f"FAILED ({len(failed)}): " + (", ".join(failed) or "-"))
    if failed:
        print("\nRun the same command again - finished files are skipped and partial ones resume.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())