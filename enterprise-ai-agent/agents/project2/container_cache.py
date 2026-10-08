"""One-time migration of an existing, verified local embedding cache."""
import hashlib
import os
import shutil
import sqlite3
from pathlib import Path


def seed_cache(source:Path,target:Path,expected_sha256:str)->dict:
    digest=hashlib.sha256()
    with source.open('rb') as stream:
        while chunk:=stream.read(1024*1024):digest.update(chunk)
    if digest.hexdigest()!=expected_sha256:raise ValueError('Cache seed hash mismatch')
    with sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True) as connection:
        columns=[r[1] for r in connection.execute('PRAGMA table_info(embeddings)')]
        if columns!=['key','vector']:raise ValueError('Unexpected cache schema')
    if target.exists():return {'mode':'retained_existing_cache','seed_sha256':expected_sha256}
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_name(target.name+'.seed.tmp')
    with temporary.open('xb') as output,source.open('rb') as stream:shutil.copyfileobj(stream,output)
    os.replace(temporary,target)
    return {'mode':'verified_existing_host_cache_migrated','seed_sha256':expected_sha256}
