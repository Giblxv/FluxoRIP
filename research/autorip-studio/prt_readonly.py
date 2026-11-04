"""Leitor experimental PRT: SOMENTE LEITURA, sem dependências externas.

O cabeçalho observado em UMA amostra sugere inteiros little-endian nos offsets
12 (linhas), 16 (stride), 28 (faixas). Não inferir canais ou layout dos pixels.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import struct

HEADER_BYTES = 48
MAX_FILE_BYTES = 8 * 1024**3
MAX_LINES = 10_000_000
MAX_STRIDE = 1_000_000
MAX_BANDS = 64


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
    """Analisa arquivo imutavelmente; falha se tamanho/mtime mudarem durante leitura."""
    p = Path(path)
    before = p.stat()
    if not p.is_file() or before.st_size < HEADER_BYTES or before.st_size > max_bytes:
        raise PRTValidationError("Tamanho de arquivo inválido ou fora do limite")
    digest = sha256()
    with p.open("rb") as stream:
        header = stream.read(HEADER_BYTES)
        digest.update(header)
        signature = struct.unpack_from("<H", header, 0)[0]
        lines, stride, bands = (struct.unpack_from("<I", header, off)[0]
                                for off in (12, 16, 28))
        if signature != 0x5555:
            raise PRTValidationError("Assinatura PRT candidata 0x5555 ausente")
        if not (0 < lines <= MAX_LINES and 0 < stride <= MAX_STRIDE and 0 < bands <= MAX_BANDS):
            raise PRTValidationError("Dimensões do cabeçalho fora dos limites")
        if HEADER_BYTES + lines * bands * stride != before.st_size:
            raise PRTValidationError("Geometria do cabeçalho incompatível com tamanho")
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after = p.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size, after.st_mtime_ns, after.st_ino):
        raise PRTValidationError("Arquivo mudou durante análise; resultado descartado")
    return PRTInfo(str(p), before.st_size, digest.hexdigest(),
                   signature, lines, stride, bands)


def compare_band_bytes(path_a, path_b, *, layout="row-major", max_bytes=MAX_FILE_BYTES):
    """Conta diferenças por faixa; NÃO identifica tintas CMYKW.

    row-major: [linha][faixa][stride]; plane-major: [faixa][linha][stride].
    Exige geometria igual e lê no máximo um stride por vez.
    """
    if layout not in ("row-major", "plane-major"):
        raise ValueError("Layout inválido")
    a = inspect_prt(path_a, max_bytes=max_bytes)
    b = inspect_prt(path_b, max_bytes=max_bytes)
    if (a.lines, a.stride, a.bands) != (b.lines, b.stride, b.bands):
        raise PRTValidationError("Geometrias diferentes; comparação recusada")
    differences = [0] * a.bands
    with open(path_a, "rb") as fa, open(path_b, "rb") as fb:
        for band in range(a.bands):
            for line in range(a.lines):
                index = ((line * a.bands + band) if layout == "row-major"
                         else (band * a.lines + line))
                offset = HEADER_BYTES + index * a.stride
                fa.seek(offset)
                fb.seek(offset)
                aa, bb = fa.read(a.stride), fb.read(a.stride)
                if len(aa) != a.stride or len(bb) != b.stride:
                    raise PRTValidationError("Leitura truncada")
                differences[band] += sum(x != y for x, y in zip(aa, bb))
    # SHA novamente após a comparação para detectar alterações durante o percurso.
    if inspect_prt(path_a, max_bytes=max_bytes).sha256 != a.sha256:
        raise PRTValidationError("Arquivo A alterado durante comparação")
    if inspect_prt(path_b, max_bytes=max_bytes).sha256 != b.sha256:
        raise PRTValidationError("Arquivo B alterado durante comparação")
    return {"layout_hypothesis": layout, "sha256_a": a.sha256,
            "sha256_b": b.sha256, "different_bytes_by_band": differences,
            "total_different_bytes": sum(differences)}
