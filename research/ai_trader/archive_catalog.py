"""Extract only the previously verified XAUUSD ParquetDataCatalog from pinned archive."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

SHA256="56bf3bcfc3221b6cccd9cd64c03425952ebc98baf510e39058b65372772bdf38"
PREFIX="xauusd-data/.work/vibe-math-xauusd-20260727/"
def extract(archive,target):
    archive=Path(archive)
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest!=SHA256:
        raise ValueError("pinned archive SHA256 mismatch")
    target=Path(target).resolve()
    catalog=target/PREFIX.rstrip("/")
    with zipfile.ZipFile(archive) as z:
        members=[x for x in z.infolist() if x.filename.startswith(PREFIX) and not x.is_dir()]
        if not any(x.filename.endswith(".parquet") for x in members):
            raise ValueError("no real XAUUSD parquet catalog in pinned archive")
        for item in members:
            path=(target/item.filename).resolve()
            if not path.is_relative_to(target):
                raise ValueError("unsafe archive member")
            path.parent.mkdir(parents=True,exist_ok=True)
            with z.open(item) as src,path.open("wb") as dst:
                import shutil
                shutil.copyfileobj(src,dst)
    if not catalog.exists():
        raise ValueError("catalog extraction failed")
    return {"catalog_path":str(catalog),"archive_sha256":digest,"parquet_files":len(members)}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive",required=True)
    p.add_argument("--target",required=True)
    p.add_argument("--manifest",required=True)
    a=p.parse_args()
    result=extract(a.archive,a.target)
    Path(a.manifest).write_text(json.dumps(result,indent=2))
    print("VERIFIED_ARCHIVE_CATALOG",result["parquet_files"])
if __name__=="__main__":main()
