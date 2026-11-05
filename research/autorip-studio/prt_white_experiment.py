"""Leitura estática comparativa de três PRTs (0/50/100% branco declarados).

Os percentuais são rótulos fornecidos pelo operador, não são inferidos dos bytes.
Não produz PRT ou imprime. Não associa faixas a canais físicos.
"""
import argparse
import json
from pathlib import Path

from layout_hypotheses import inspect
from prt_diff import compare

LABELS = ('white_0', 'white_50', 'white_100')


def analyze_white_levels(paths, *, block_size=65536):
    """Compara a mesma arte rasterizada sob três configurações declaradas.

    Exige geometria consistente e exatamente 12 faixas candidatas.
    Se hashes forem idênticos, registra a igualdade sem presumir o porquê.
    """
    if set(paths) != set(LABELS) or len(paths) != 3:
        raise ValueError('Required labels: white_0, white_50, white_100')
    resolved = {name: Path(paths[name]).resolve(strict=True) for name in LABELS}
    if len(set(resolved.values())) != 3:
        raise ValueError('Each level must refer to a different original file')
    info = {name: inspect(resolved[name]) for name in LABELS}
    geom = lambda i: (i['rows_candidate'], i['slots_candidate'], i['stride_candidate'])
    if len({geom(i) for i in info.values()}) != 1:
        raise ValueError('All three levels must have identical candidate geometry')
    rows, slots, stride = geom(info['white_0'])
    if slots != 12:
        raise ValueError('This controlled comparison requires exactly 12 candidate slots')
    pairs = {}
    for a, b in (('white_0','white_50'),('white_50','white_100'),('white_0','white_100')):
        report = compare(resolved[a], resolved[b], block_size=block_size)
        pairs[f'{a}_vs_{b}'] = {
            'a_sha256': report['a_sha256'], 'b_sha256': report['b_sha256'],
            'identical': report['same_content'],
            'header_changed_offsets': report['header_changed_offsets'],
            'candidate_layouts': {
                hypothesis: {
                    'changed_bytes_by_slot': [v['different_bytes'] for v in entries],
                    'total_changed_bytes': sum(v['different_bytes'] for v in entries),
                } for hypothesis, entries in report['hypotheses'].items()
            },
        }
    return {
        'labels_are_operator_declared': True,
        'candidate_geometry': {'rows': rows, 'slots': slots, 'stride': stride,
                               'expected_bytes': 48 + rows*slots*stride},
        'sources': {name: {'sha256': info[name]['sha256'],
                           'size_bytes': info[name]['size_bytes']} for name in LABELS},
        'pairwise': pairs,
        'color_channel_mapping': 'unverified',
        'layout_mapping': 'unverified',
        'warning': 'A difference is not proof of white ink channels, percentage or physical compatibility.'
    }


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Read-only three-PRT white-setting experiment')
    ap.add_argument('--white-0', required=True)
    ap.add_argument('--white-50', required=True)
    ap.add_argument('--white-100', required=True)
    ap.add_argument('--block-size', type=int, default=65536)
    args = ap.parse_args()
    data = analyze_white_levels({'white_0':args.white_0,'white_50':args.white_50,
                                 'white_100':args.white_100},block_size=args.block_size)
    print(json.dumps(data, indent=2, ensure_ascii=False))
