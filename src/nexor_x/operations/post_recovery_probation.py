from __future__ import annotations
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import threading
from typing import Any

@dataclass(frozen=True)
class PostRecoveryProbationPolicy:
    probation_seconds: int = 60 * 60
    min_entry_interval_seconds: int = 15 * 60
    max_entries_during_probation: int = 3

class _SuccessfulEntryTransaction:
    def __init__(self, controller: "PostRecoveryProbationController", *, action: str, bypass: bool) -> None:
        self.controller = controller
        self.action = action
        self.bypass = bypass
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None and not self.bypass:
            self.controller.record_successful_entry(action=self.action)
        return False

class PostRecoveryProbationController:
    def __init__(self, *, state_path: str | Path | None = None, policy: PostRecoveryProbationPolicy | None = None) -> None:
        self.policy = policy or PostRecoveryProbationPolicy()
        self.state_path = Path(state_path) if state_path else None
        self._lock = threading.RLock()
        self._state: dict[str, Any] = {
            'active': False, 'started_at': None, 'last_entry_at': None,
            'admitted_entries': 0, 'last_success_action': None,
        }
        self._load()

    def successful_entry_transaction(self, *, action: str, bypass: bool = False) -> _SuccessfulEntryTransaction:
        return _SuccessfulEntryTransaction(self, action=action, bypass=bypass)

    def start(self, *, now: datetime | None = None) -> dict[str, Any]:
        now = self._utc(now)
        with self._lock:
            self._state = {'active': True, 'started_at': now.isoformat(), 'last_entry_at': None,
                           'admitted_entries': 0, 'last_success_action': None}
            self._save()
            return self.status(now=now)

    def evaluate(self, *, degradation: dict[str, Any], action: str, reduce_only: bool = False,
                 now: datetime | None = None) -> dict[str, Any]:
        now = self._utc(now)
        with self._lock:
            raw_state = str(degradation.get('state','NORMAL')).upper()
            protective = bool(reduce_only)
            if self._state['active'] and self._can_finish(now, raw_state):
                self._state = {'active':False,'started_at':None,'last_entry_at':None,
                               'admitted_entries':0,'last_success_action':None}
                self._save()
            active = bool(self._state['active'])
            block_reason = None
            if protective:
                allowed = True
            elif not active:
                allowed = bool(degradation.get('new_entries_allowed', True))
            elif raw_state != 'NORMAL':
                allowed = False; block_reason='probation_requires_normal_state'
            elif int(self._state['admitted_entries']) >= self.policy.max_entries_during_probation:
                allowed = False; block_reason='probation_entry_limit_reached'
            elif not self._entry_interval_elapsed(now):
                allowed = False; block_reason='probation_entry_interval_active'
            else:
                allowed = bool(degradation.get('new_entries_allowed', True))
            effective = dict(degradation)
            if not allowed and not protective:
                effective['state']='BLOCKED'; effective['new_entries_allowed']=False
                hard=list(effective.get('hard_reasons') or [])
                if block_reason and block_reason not in hard: hard.append(block_reason)
                effective['hard_reasons']=hard
            return {'active':active,'action':str(action).upper(),'reduce_only':protective,
                    'raw_state':raw_state,'allowed':allowed,'block_reason':block_reason,
                    'admitted_entries':int(self._state['admitted_entries']),
                    'max_entries_during_probation':self.policy.max_entries_during_probation,
                    'probation_seconds':self.policy.probation_seconds,
                    'min_entry_interval_seconds':self.policy.min_entry_interval_seconds,
                    'elapsed_seconds':self._elapsed(now),'remaining_seconds':self._remaining(now),
                    'degradation':effective,'live_allowed':False,'evaluated_at':now.isoformat()}

    def record_successful_entry(self, *, action: str, now: datetime | None = None) -> dict[str, Any]:
        now = self._utc(now)
        with self._lock:
            if not self._state['active']:
                return {'committed':False,'reason':'PROBATION_NOT_ACTIVE', **self.status(now=now)}
            if int(self._state['admitted_entries']) >= self.policy.max_entries_during_probation:
                return {'committed':False,'reason':'PROBATION_ENTRY_LIMIT_REACHED', **self.status(now=now)}
            self._state['admitted_entries'] = int(self._state['admitted_entries']) + 1
            self._state['last_entry_at'] = now.isoformat()
            self._state['last_success_action'] = str(action).upper()
            self._save()
            return {'committed':True,'reason':'SUCCESSFUL_ENTRY_COMMITTED', **self.status(now=now)}

    def admit(self, *, degradation: dict[str, Any], action: str, reduce_only: bool = False,
              now: datetime | None = None) -> dict[str, Any]:
        report = self.evaluate(degradation=degradation, action=action, reduce_only=reduce_only, now=now)
        if not report['allowed'] or reduce_only or not report['active']:
            return report
        commit = self.record_successful_entry(action=action, now=now)
        report['admitted_entries'] = commit['admitted_entries']
        return report

    def status(self, *, now: datetime | None = None) -> dict[str, Any]:
        now = self._utc(now)
        with self._lock:
            return {'active':bool(self._state['active']),'started_at':self._state.get('started_at'),
                    'last_entry_at':self._state.get('last_entry_at'),
                    'last_success_action':self._state.get('last_success_action'),
                    'admitted_entries':int(self._state['admitted_entries']),
                    'max_entries_during_probation':self.policy.max_entries_during_probation,
                    'probation_seconds':self.policy.probation_seconds,
                    'min_entry_interval_seconds':self.policy.min_entry_interval_seconds,
                    'elapsed_seconds':self._elapsed(now),'remaining_seconds':self._remaining(now),
                    'live_allowed':False,'evaluated_at':now.isoformat()}

    def _can_finish(self, now: datetime, raw_state: str) -> bool:
        return self._elapsed(now) >= self.policy.probation_seconds and raw_state == 'NORMAL'
    def _entry_interval_elapsed(self, now: datetime) -> bool:
        last=self._parse_dt(self._state.get('last_entry_at'))
        return True if last is None else (now-last).total_seconds() >= self.policy.min_entry_interval_seconds
    def _elapsed(self, now: datetime) -> float:
        started=self._parse_dt(self._state.get('started_at'))
        return 0.0 if started is None else max(0.0,(now-started).total_seconds())
    def _remaining(self, now: datetime) -> float:
        return 0.0 if not self._state['active'] else max(0.0,self.policy.probation_seconds-self._elapsed(now))
    def _load(self) -> None:
        if self.state_path is None or not self.state_path.exists(): return
        try: payload=json.loads(self.state_path.read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError): return
        if isinstance(payload,dict):
            for k in self._state:
                if k in payload: self._state[k]=payload[k]
    def _save(self) -> None:
        if self.state_path is None: return
        self.state_path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.state_path.with_suffix(self.state_path.suffix+'.tmp')
        tmp.write_text(json.dumps(self._state,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        tmp.replace(self.state_path)
    @staticmethod
    def _parse_dt(value: Any) -> datetime | None:
        if not value: return None
        try: parsed=datetime.fromisoformat(str(value))
        except ValueError: return None
        if parsed.tzinfo is None: parsed=parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    @staticmethod
    def _utc(value: datetime | None) -> datetime:
        if value is None: return datetime.now(UTC)
        if value.tzinfo is None: return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
