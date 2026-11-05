"""API compatível de leitura PRT usando o analisador canônico da pesquisa.

Não oferece geração de PRT nem comunicação com equipamentos. Faixas != tintas.
"""
from dataclasses import dataclass
from pathlib import Path

from layout_hypotheses import inspect, HEADER, MAX_INPUT_BYTES
from prt_diff import compare

HEADER_BYTES = HEADER
MAX_FILE_BYTES = MAX_INPUT_BYTES


class PRTValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PRTInfo:
    path: str
    file_size: int
    sha256: str
    signature: int
    lines: int
    stride: int
    bands: int
    header_bytes: int = HEADER_BYTES

    @property
    def payload_bytes(self):
        return self.file_size - self.header_bytes


def inspect_prt(path, *, max_bytes=MAX_FILE_BYTES):
    try:
        meta = inspect(path, max_bytes=max_bytes)
    except (OSError, ValueError, OverflowError) as exc:
        raise PRTValidationError(str(exc)) from exc
    return PRTInfo(str(Path(path)), meta['size_bytes'], meta['sha256'],
                   0x5555, meta['rows_candidate'], meta['stride_candidate'],
                   meta['slots_candidate'])


def compare_band_bytes(path_a, path_b, *, layout='row-major', max_bytes=MAX_FILE_BYTES):
    """Compatibilidade com a API antiga; análise real usa ambas as hipóteses."""
    lookup = {'row-major': 'row_major', 'plane-major': 'plane_major'}
    if layout not in lookup:
        raise ValueError('Layout inválido')
    aa, bb = inspect_prt(path_a, max_bytes=max_bytes), inspect_prt(path_b, max_bytes=max_bytes)
    if (aa.lines, aa.stride, aa.bands) != (bb.lines, bb.stride, bb.bands):
        raise PRTValidationError('Geometrias diferentes; comparação recusada')
    try:
        report = compare(path_a, path_b)
    except (OSError, ValueError) as exc:
        raise PRTValidationError(str(exc)) from exc
    entries = report['hypotheses'][lookup[layout]]
    values = [item['different_bytes'] for item in entries]
    return {'layout_hypothesis': layout,
            'sha256_a': report['a_sha256'], 'sha256_b': report['b_sha256'],
            'different_bytes_by_band': values, 'total_different_bytes': sum(values)}
