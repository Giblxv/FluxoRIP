from dataclasses import dataclass


@dataclass
class HosonAdapter:
    """Readiness description only; no sockets or printer commands.

    PrintExp Ethernet variants differ. Even if a TCP port is documented for
    a particular version, use a model/firmware-specific validated adapter.
    """
    printer_id: str
    ip: str | None = None
    firmware: str | None = None
    printexp_version: str | None = None

    def health(self) -> dict:
        return {
            'printer_id': self.printer_id,
            'controller': 'Hoson',
            'mode': 'observe_only',
            'connected': None,
            'printer_status': 'NAO_VERIFICADO',
            'note': 'Sem telemetria de máquina. Nenhum comando de rede foi enviado.',
        }
