"""Portable finite reuse checks, separate from the retained 68-test receipt.

Only pure model functions run. On Windows a deny-all import stub permits importing
pair_bank's POSIX-oriented CLI module; no resource measurement/limit call is used.
"""
import copy
import functools
import itertools
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import hierarchy
# In an actual-code comparison, hierarchy is preloaded from the selected tree.
sys.path.insert(0, str(Path(hierarchy.__file__).resolve().parent))
try:
    import resource
except ModuleNotFoundError:
    resource = types.ModuleType('resource')
    def deny(name):
        raise RuntimeError('POSIX CLI operations are not part of this pure test: ' + name)
    resource.__getattr__ = deny
    sys.modules['resource'] = resource
import pair_bank
import pooled_hierarchy
import verify_hierarchy
import verify_pooled

def serial(value):
    return json.loads(json.dumps(value))

def load(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))

def literal_first_difference(move, root, alphabet, observer, maximum):
    """Enumerate literal words, without a visited set, paired BFS or reuse cache."""
    choices = list(itertools.product(alphabet, repeat=3))
    for depth in range(1, maximum + 1):
        for word in itertools.product(choices, repeat=depth):
            left = right = root
            trace = []
            for own, other_left, other_right in word:
                u = (own, other_left) if observer == 0 else (other_left, own)
                v = (own, other_right) if observer == 0 else (other_right, own)
                left, x = move(left, u)
                right, y = move(right, v)
                trace.append({'left_input': list(u), 'right_input': list(v),
                              'left_output': x[observer], 'right_output': y[observer]})
                if x[observer] != y[observer]:
                    return serial(trace)
    return None

@functools.lru_cache(maxsize=1)
def snapshot():
    logical = []
    for mode in hierarchy.MODES:
        for observer in (0, 1):
            raw = serial(hierarchy.pair_check(mode, observer))
            assert raw == load(f'results/hierarchy-{mode}-{observer}.json')
            logical.append({'raw': raw, 'verification': verify_hierarchy.verify(raw)})
    pooled = []
    for caps in ((1, 1), (1, 2), (2, 1)):
        stem = ''.join(map(str, caps))
        obj = load(f'inputs/hierarchy-pool-{stem}.json')
        cert = load(f'results/hierarchy-pool-{stem}.certificate.json')
        for policy in ('first-fit', 'certified'):
            if policy == 'certified' and cert['conclusion'] != 'realizable':
                continue
            machine = pooled_hierarchy.Machine(caps, obj if policy == 'certified' else None,
                                                cert if policy == 'certified' else None)
            for observer in (0, 1):
                raw = serial(pooled_hierarchy.check(machine, observer))
                raw.update(capacities=list(caps), policy=policy)
                assert raw == load(f'results/pooled-{stem}-{policy}-{observer}.json')
                pooled.append({'raw': raw, 'verification': verify_pooled.verify(raw, obj, cert)})
    bank = []
    for kind, caps in (('protected', (1, 1, 1)), ('negative', (1, 1, 0))):
        for observer in (0, 1):
            raw = serial(pair_bank.paired(caps, observer))
            raw.update(capacities=list(caps), observer=observer)
            raw.update(verification=pair_bank.verify(raw), workers=1)
            retained = load(f'results/pair-bank-{kind}-{observer}.json')
            # Exactly the CLI's scientific envelope; only its three declared
            # measurement fields are absent from this non-measuring pure call.
            retained = {k: v for k, v in retained.items()
                        if k not in ('cpu_seconds', 'wall_seconds', 'peak_rss_kib')}
            assert raw == retained
            bank.append({'raw': raw, 'verification': raw['verification']})
    errors = []
    for label, run in (
        ('logical-cap', lambda: hierarchy.pair_check('protected', 0, limit=1)),
        ('pool-cap', lambda: pooled_hierarchy.check(pooled_hierarchy.Machine((1, 2)), 0, limit=1)),
        ('bank-capacity', lambda: pair_bank.paired((1, 1, 7), 0)),
        ('bank-observer', lambda: pair_bank.paired((1, 1, 1), True)),
        ('mode', lambda: hierarchy.pair_check('invalid', 0)),
    ):
        try:
            run()
        except (ValueError, RuntimeError) as exc:
            errors.append([label, type(exc).__name__, str(exc)])
        else:
            raise AssertionError('missing refusal: ' + label)
    return {'logical': logical, 'pooled': pooled, 'bank': bank, 'refusals': errors}

class PairReuseTests(unittest.TestCase):
    def test_full_retained_certificates_and_scientific_counters(self):
        result = snapshot()
        self.assertEqual([len(result[k]) for k in ('logical', 'pooled', 'bank', 'refusals')],
                         [10, 10, 4, 5])
        # Negative/positive interleaving above must not leave an instance/global cache.
        self.assertEqual(serial(hierarchy.pair_check('protected', 0)), result['logical'][0]['raw'])

    def test_literal_tiny_words_and_tamper_rejections(self):
        for observer in (0, 1):
            expected = literal_first_difference(
                lambda s, u: verify_hierarchy.tick(s, u, 'global-credit'),
                verify_hierarchy.ZERO, verify_hierarchy.SYMBOLS, observer, 2)
            self.assertEqual(serial(hierarchy.pair_check('global-credit', observer))['trace'], expected)
            expected = literal_first_difference(
                lambda s, u: pair_bank.reference(s, u, (1, 1, 0)),
                pair_bank.ROOT, pair_bank.INPUT, observer, 2)
            self.assertEqual(serial(pair_bank.paired((1, 1, 0), observer))['trace'], expected)
        expected = literal_first_difference(
            lambda s, u: verify_pooled.reference_step(s, u, (1, 1)),
            verify_pooled.ROOT, verify_hierarchy.SYMBOLS, 1, 1)
        self.assertEqual(serial(pooled_hierarchy.check(pooled_hierarchy.Machine((1, 1)), 1))['trace'], expected)
        result = snapshot()
        for group, check in (('logical', verify_hierarchy.verify),
                             ('pooled', verify_pooled.verify), ('bank', pair_bank.verify)):
            raw = result[group][0]['raw']
            for field in ('checked_edges', 'visited_pairs'):
                broken = copy.deepcopy(raw); broken[field] += 1
                with self.assertRaises(ValueError):
                    check(broken)
            broken = copy.deepcopy(raw); broken['closed_relation'].pop()
            with self.assertRaises(ValueError):
                check(broken)

    def test_local_lazy_reuse_and_unchanged_semantic_edge_meaning(self):
        for module, attribute, root, alphabet in (
            (hierarchy, 'step', hierarchy.EMPTY, hierarchy.ALPHABET),
            (pair_bank, 'transition', pair_bank.ROOT, pair_bank.INPUT),
            (pooled_hierarchy, None, pooled_hierarchy.ROOT, hierarchy.ALPHABET),
        ):
            calls = []
            def toy(state, inputs, *unused):
                calls.append((state, inputs))
                next_state = (1-state[0], *root[1:])
                return next_state, ((-1, ()), (-1, ()))
            if attribute:
                with patch.object(module, attribute, toy):
                    raw = hierarchy.pair_check('protected', 0) if module is hierarchy else pair_bank.paired((1, 1, 1), 0)
            else:
                machine = types.SimpleNamespace(tick=toy)
                raw = pooled_hierarchy.check(machine, 0)
            self.assertEqual(raw['visited_pairs'], 2)
            self.assertEqual(raw['checked_edges'], 2*len(alphabet)**3)
            self.assertEqual(len(calls), 4*len(alphabet)**2)
            self.assertEqual(serial(raw['closed_relation']),
                             [[list(root), list(root)],
                              [[1, *root[1:]], [1, *root[1:]]]])
        calls = []
        def distinguish(state, inputs, *unused):
            calls.append(inputs)
            return state, ((inputs[1], ()), (-1, ()))
        with patch.object(hierarchy, 'step', distinguish):
            raw = hierarchy.pair_check('protected', 0)
        self.assertEqual(raw['checked_edges'], 2)
        self.assertEqual(calls, [(-1, -1), (-1, -1), (-1, 0)])
        self.assertEqual(raw['shortest_ticks'], 1)

if __name__ == '__main__':
    unittest.main()
