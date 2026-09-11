import os
import json
import sqlite3
import datetime
import urllib.request
import threading
import time
from .models import clean_provider_name, clean_model_display_name, format_num, format_time_ago, format_time_left

DB_PATH = os.path.expandvars(r'%APPDATA%\9router\db\data.sqlite')

class DataService:
    def __init__(self, on_data_updated=None):
        self.on_data_updated = on_data_updated
        self.last_max_id = 0
        self.last_rd_rowid = 0
        self.last_activity_time = 0.0
        self.last_activity_is_error = False
        self.last_delta_tokens = 0
        self.last_delta_time = 0.0
        self.latest_tps = None
        self.live_quotas_cache = {}
        self._fetching_conn_ids = set()

        self.default_account_quotas = {
            'antigravity': 200_000_000,
            'codex': 150_000_000,
            'gemini': 200_000_000,
            'kilocode': 100_000_000,
            'default': 100_000_000
        }
        self.custom_quotas = {}

    def fetch_live_quota(self, conn_id, is_9router_running):
        if not is_9router_running or not conn_id:
            return None
        now = time.time()
        cached = self.live_quotas_cache.get(conn_id)
        is_stale = (not cached) or (now - cached['time']) >= 15.0

        if is_stale and conn_id not in self._fetching_conn_ids:
            self._fetching_conn_ids.add(conn_id)
            threading.Thread(target=self._async_fetch_live_quota, args=(conn_id,), daemon=True).start()

        return cached['data'] if cached else None

    def _async_fetch_live_quota(self, conn_id):
        try:
            url = f'http://127.0.0.1:20128/api/usage/{conn_id}'
            req = urllib.request.Request(url, headers={'User-Agent': 'DynamicTokenHUD/1.0'})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read())
                    self.live_quotas_cache[conn_id] = {'time': time.time(), 'data': data}
                    if self.on_data_updated:
                        self.on_data_updated()
        except Exception:
            pass
        finally:
            self._fetching_conn_ids.discard(conn_id)

    def get_account_quota_limit(self, prov_name, acc_id_or_email):
        if acc_id_or_email in self.custom_quotas:
            return self.custom_quotas[acc_id_or_email]
        if prov_name in self.custom_quotas:
            return self.custom_quotas[prov_name]
        return self.default_account_quotas.get(prov_name, self.default_account_quotas['default'])

    def toggle_account_active(self, conn_id, current_status):
        if not os.path.exists(DB_PATH) or not conn_id:
            return
        try:
            con = sqlite3.connect(DB_PATH, timeout=5.0)
            cur = con.cursor()
            new_val = 0 if current_status else 1
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute('UPDATE providerConnections SET isActive = ?, updatedAt = ? WHERE id = ?', (new_val, now_iso, conn_id))
            con.commit()
            con.close()
        except Exception:
            pass

    def toggle_provider_active(self, prov_name, current_any_active):
        if not os.path.exists(DB_PATH) or not prov_name:
            return
        try:
            con = sqlite3.connect(DB_PATH, timeout=5.0)
            cur = con.cursor()
            new_val = 0 if current_any_active else 1
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute('UPDATE providerConnections SET isActive = ?, updatedAt = ? WHERE provider = ?', (new_val, now_iso, prov_name))
            con.commit()
            con.close()
        except Exception:
            pass

    def fetch_stats(self, timeline='today', is_9router_running=False):
        if not os.path.exists(DB_PATH):
            return None
        try:
            con = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
            cur = con.cursor()

            row = cur.execute('SELECT MAX(id) FROM usageHistory').fetchone()
            max_id = row[0] if row and row[0] else 0
            if max_id > self.last_max_id:
                if self.last_max_id != 0:
                    self.last_activity_time = time.time()
                    self.last_activity_is_error = False
                    latest_call = cur.execute('SELECT promptTokens, completionTokens, status FROM usageHistory WHERE id = ?', (max_id,)).fetchone()
                    if latest_call:
                        self.last_delta_tokens = (latest_call[0] or 0) + (latest_call[1] or 0)
                        self.last_delta_time = time.time()
                        if latest_call[2] != 'ok':
                            self.last_activity_is_error = True
                self.last_max_id = max_id

            rd_latest = cur.execute('SELECT rowid, status, data FROM requestDetails ORDER BY rowid DESC LIMIT 1').fetchone()
            if rd_latest:
                rd_rowid, rd_status, rd_data_str = rd_latest
                if rd_rowid > self.last_rd_rowid:
                    if self.last_rd_rowid != 0:
                        if rd_status == 'error':
                            self.last_activity_time = time.time()
                            self.last_activity_is_error = True
                    self.last_rd_rowid = rd_rowid

                try:
                    rd_obj = json.loads(rd_data_str)
                    lat_obj = rd_obj.get('latency', {})
                    tok_obj = rd_obj.get('tokens', {})
                    c_tok = tok_obj.get('completion_tokens', 0)
                    tot_ms = lat_obj.get('total', 0)
                    ttft_ms = lat_obj.get('ttft', 0)
                    gen_ms = tot_ms - ttft_ms
                    if c_tok > 0 and gen_ms >= 80:
                        self.latest_tps = c_tok / (gen_ms / 1000.0)
                    elif c_tok > 0 and tot_ms >= 100:
                        self.latest_tps = c_tok / (tot_ms / 1000.0)
                except Exception:
                    pass

            today_str = datetime.date.today().isoformat()
            if timeline == 'today':
                rows = cur.execute('SELECT dateKey, data FROM usageDaily WHERE dateKey = ?', (today_str,)).fetchall()
            elif timeline == '7d':
                start_str = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
                rows = cur.execute('SELECT dateKey, data FROM usageDaily WHERE dateKey >= ?', (start_str,)).fetchall()
            elif timeline == '30d':
                start_str = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
                rows = cur.execute('SELECT dateKey, data FROM usageDaily WHERE dateKey >= ?', (start_str,)).fetchall()
            else:
                rows = cur.execute('SELECT dateKey, data FROM usageDaily').fetchall()

            reqs = 0
            prompt = 0
            comp = 0
            cached = 0
            cost = 0.0
            by_model = {}
            today_acc_stats = {}

            curr_quota_acc_tokens = {}
            t_row = cur.execute('SELECT data FROM usageDaily WHERE dateKey = ?', (today_str,)).fetchone()
            if t_row:
                try:
                    td = json.loads(t_row[0])
                    for acc_id, a_stat in td.get('byAccount', {}).items():
                        curr_quota_acc_tokens[acc_id] = (a_stat.get('promptTokens', 0) or 0) + (a_stat.get('completionTokens', 0) or 0)
                except Exception:
                    pass

            for r in rows:
                try:
                    d = json.loads(r[1])
                    reqs += d.get('requests', 0)
                    prompt += d.get('promptTokens', 0)
                    comp += d.get('completionTokens', 0)
                    cached += d.get('cachedTokens', 0)
                    cost += d.get('cost', 0.0)
                    for m_key, mstat in d.get('byModel', {}).items():
                        clean = m_key.split('|')[0]
                        if clean not in by_model:
                            by_model[clean] = {'requests': 0, 'prompt': 0, 'completion': 0, 'cached': 0, 'cost': 0.0}
                        by_model[clean]['requests'] += mstat.get('requests', 0)
                        by_model[clean]['prompt'] += mstat.get('promptTokens', 0)
                        by_model[clean]['completion'] += mstat.get('completionTokens', 0)
                        by_model[clean]['cached'] += mstat.get('cachedTokens', 0)
                        by_model[clean]['cost'] += mstat.get('cost', 0.0)
                    for acc_id, a_stat in d.get('byAccount', {}).items():
                        if acc_id not in today_acc_stats:
                            today_acc_stats[acc_id] = {'requests': 0, 'promptTokens': 0, 'completionTokens': 0, 'cost': 0.0}
                        today_acc_stats[acc_id]['requests'] += a_stat.get('requests', 0)
                        today_acc_stats[acc_id]['promptTokens'] += a_stat.get('promptTokens', 0)
                        today_acc_stats[acc_id]['completionTokens'] += a_stat.get('completionTokens', 0)
                        today_acc_stats[acc_id]['cost'] += a_stat.get('cost', 0.0)
                except Exception:
                    pass

            recent_rows = cur.execute(
                'SELECT id, timestamp, provider, model, promptTokens, completionTokens, cost, status FROM usageHistory ORDER BY id DESC LIMIT 5'
            ).fetchall()

            latest_m = recent_rows[0][3] if recent_rows else '--'

            latest_latency = None
            tot_reasoning = 0
            latest_conn_id = None
            try:
                req_details_row = cur.execute('SELECT data FROM requestDetails ORDER BY id DESC LIMIT 1').fetchone()
                if req_details_row:
                    rd = json.loads(req_details_row[0])
                    latest_latency = rd.get('latency', {})
                    latest_conn_id = rd.get('connectionId')

                time_filter = today_str if timeline == 'today' else (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
                for r in cur.execute('SELECT data FROM requestDetails WHERE timestamp >= ?', (time_filter,)).fetchall():
                    try:
                        d = json.loads(r[0])
                        tok = d.get('tokens', {})
                        tot_reasoning += tok.get('reasoning_tokens', 0)
                    except: pass
            except Exception:
                pass

            raw_conns = cur.execute('SELECT id, provider, name, email, priority, isActive, data FROM providerConnections ORDER BY provider, priority ASC').fetchall()
            providers_map = {}

            for r in raw_conns:
                raw_prov = r[1]
                if raw_prov not in providers_map:
                    providers_map[raw_prov] = []

                is_active = bool(r[5])
                full_email = r[3] or r[2] or '--'
                short_user = full_email.split('@')[0]
                astats = today_acc_stats.get(r[0], {})
                a_reqs = astats.get('requests', 0)
                a_toks = astats.get('promptTokens', 0) + astats.get('completionTokens', 0)
                a_cost = astats.get('cost', 0.0)
                a_curr_quota_toks = curr_quota_acc_tokens.get(r[0], 0)
                is_curr = (latest_conn_id and r[0] == latest_conn_id)

                a_reset_at = None
                if r[6]:
                    try:
                        c_data = json.loads(r[6])
                        a_reset_at = c_data.get('lastPingedResetAt') or c_data.get('resetsAt') or c_data.get('expiresAt')
                    except Exception:
                        pass

                providers_map[raw_prov].append({
                    'id': r[0],
                    'provider': raw_prov,
                    'short_user': short_user,
                    'full_email': full_email,
                    'priority': r[4],
                    'is_active': is_active,
                    'is_current': is_curr,
                    'reqs': a_reqs,
                    'toks': a_toks,
                    'cost': a_cost,
                    'quota_toks': a_curr_quota_toks,
                    'reset_at': a_reset_at
                })

            providers_data = []
            for p_name, accs in providers_map.items():
                active_cnt = sum(1 for a in accs if a['is_active'])
                total_cnt = len(accs)
                total_p_toks = sum(a['toks'] for a in accs)
                total_p_reqs = sum(a['reqs'] for a in accs)
                has_current = any(a['is_current'] for a in accs)

                providers_data.append({
                    'raw_name': p_name,
                    'clean_name': clean_provider_name(p_name),
                    'accounts': accs,
                    'active_count': active_cnt,
                    'total_count': total_cnt,
                    'total_toks': total_p_toks,
                    'total_reqs': total_p_reqs,
                    'has_current': has_current
                })

            providers_data.sort(key=lambda x: (not x['has_current'], -x['total_count'], x['clean_name']))

            con.close()
            return {
                'requests': reqs,
                'prompt': prompt,
                'completion': comp,
                'cached': cached,
                'reasoning': tot_reasoning,
                'cost': cost,
                'models': by_model,
                'recent': recent_rows,
                'latest_model': latest_m,
                'latest_latency': latest_latency,
                'providers_data': providers_data,
                'latest_conn_id': latest_conn_id
            }
        except Exception:
            return None
