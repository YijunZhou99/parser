"""Current: compares text occurrence counts and order before repair adoption.
Limitations: generic comparison cannot certify visual recovery.
TODO(B3): measure ordinary-text and table fidelity with real providers.
Acceptance: negation, repetition and synthetic order-only adoption tests.
"""
from collections import Counter
import re

def tokens(text):
    return re.findall(r'\w+|[^\w\s]', text.casefold())




def reconcile(original, proposed, allow_order_only=False):
    a, b = tokens(original), tokens(proposed)
    missing, added = Counter(a)-Counter(b), Counter(b)-Counter(a)
    adopted = bool(allow_order_only and not missing and not added)
    return {'original': original, 'proposed': proposed, 'omissions': dict(missing),
            'additions_repetition': dict(added), 'order_changed': a != b,
            'adopted': adopted, 'reason': 'SYNTHETIC_ORDER_ONLY' if adopted else 'UNCERTAIN_RETAIN_ORIGINAL'}
