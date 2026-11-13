"""Módulo de persistência e observabilidade de telemetria do DeskBot."""
import csv
import os


class Telemetria:
    """Gerencia a escrita segura de logs de telemetria em CSV e saída informativa."""

    def __init__(self, caminho_csv):
        self.caminho_csv = os.path.abspath(caminho_csv)
        self._garantir_diretorio()
        self._arquivo = None
        self._writer = None

    def _garantir_diretorio(self):
        log_dir = os.path.dirname(self.caminho_csv)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception as e:
                print(f"Aviso: não foi possível criar diretório de log '{log_dir}': {e}")

    def abrir(self):
        novo = not os.path.exists(self.caminho_csv)
        self._arquivo = open(self.caminho_csv, "a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._arquivo)
        if novo:
            self._writer.writerow(["hora", "pc", "energia", "tedio", "felicidade", "expressao", "fase"])
            self._arquivo.flush()
        return self

    def fechar(self):
        if self._arquivo and not self._arquivo.closed:
            self._arquivo.close()

    def registrar(self, agora_dt, pc, energia, tedio, felicidade, expr, fase, label_fase=None):
        if not self._writer:
            return
        hora_iso = agora_dt.isoformat(timespec="seconds")
        self._writer.writerow([
            hora_iso,
            pc,
            round(energia, 2),
            round(tedio, 2),
            round(felicidade, 2),
            expr,
            fase,
        ])
        self._arquivo.flush()
        label = label_fase or fase
        print(f"📊 [Telemetria] {hora_iso} | PC: {pc} | "
              f"E: {energia:.2f} | T: {tedio:.2f} | "
              f"F: {felicidade:.2f} | Expr: {expr} | Fase: {label}")

    def __enter__(self):
        return self.abrir()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fechar()
