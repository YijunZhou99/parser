"""Current: unavailable and fingerprint-bound fixture provider transport.
Limitations: no live inference integration.
TODO(B3/B7): add credential-backed providers under this interface.
Acceptance: unavailable provider and replay fingerprint tests.
"""
import json
from .extraction import sha

def fingerprint(payload):
    return sha(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode())


def request(kind, payload, replay=None):
    if replay is None:
        return {'status': 'unavailable', 'mode': 'unavailable', 'kind': kind,
                'reason': 'No live provider configured', 'input': payload}
    if replay.get('kind') != kind or replay.get('fingerprint') != fingerprint(payload):
        return {'status': 'rejected', 'mode': 'fixture_replay', 'reason': 'REPLAY_FINGERPRINT_MISMATCH', 'input': payload}
    return {'status': 'returned', 'mode': 'fixture_replay', 'input': payload,
            'response': replay.get('response'), 'provenance': 'synthetic resolver fixture, never evaluation reference'}
