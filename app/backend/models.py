import datetime

def format_num(n):
    if n is None:
        return '0'
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(int(n))

def format_time_ago(ts_str):
    if not ts_str:
        return '--'
    try:
        cleaned = ts_str.replace('Z', '+00:00')
        dt = datetime.datetime.fromisoformat(cleaned)
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = int((now - dt).total_seconds())
        if diff < 5:
            return 'just now'
        if diff < 60:
            return f"{diff}s ago"
        if diff < 3600:
            return f"{diff // 60}m ago"
        if diff < 86400:
            return f"{diff // 3600}h ago"
        return f"{diff // 86400}d ago"
    except Exception:
        return '--'

def format_time_left(reset_at_str):
    if not reset_at_str:
        return None
    try:
        cleaned = reset_at_str.replace('Z', '+00:00')
        dt = datetime.datetime.fromisoformat(cleaned)
        now = datetime.datetime.now(datetime.timezone.utc)
        diff_s = int((dt - now).total_seconds())
        if diff_s <= 0:
            return 'Resetting...'
        days = diff_s // 86400
        hours = (diff_s % 86400) // 3600
        mins = (diff_s % 3600) // 60
        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {mins}m"
        if mins > 0:
            return f"{mins}m"
        return f"{diff_s}s"
    except Exception:
        return None

def clean_provider_name(p):
    if not p: return '--'
    if p.startswith('openai-compatible-chat'): return 'OpenAI Chat'
    if p.startswith('openai-compatible-responses'): return 'OpenAI Resp'
    if p.startswith('anthropic-compatible'): return 'Anthropic'
    return p.capitalize()

def clean_model_display_name(m):
    if not m: return '--'
    if '/' in m:
        parts = m.split('/')
        if len(parts[-1]) >= 3:
            m = parts[-1]
    return m
