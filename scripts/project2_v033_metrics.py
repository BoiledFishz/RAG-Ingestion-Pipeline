"""Worker-level smoke flags; partial is not proof of Worker health."""
def worker_flags(row: dict) -> dict:
    result=row.get('result') or {};workers=result.get('workers',{})
    flags={key+'_failed_or_timeout':int(workers.get(key,{}).get('status','failed') in {'failed','timeout'}) for key in ('rag','database')}
    return {**flags,'any_worker_failed_or_timeout':int(any(flags.values()))}
