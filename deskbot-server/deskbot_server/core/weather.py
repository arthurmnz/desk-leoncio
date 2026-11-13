"""Serviço de clima resiliente do DeskBot utilizando Open-Meteo REST API."""
import json
import threading
import time
from urllib.error import URLError, HTTPError
import urllib.request

WMO_WEATHER_CODES = {
    0: "Céu limpo",
    1: "Predom. ensolarado",
    2: "Parcialm. nublado",
    3: "Encoberto",
    45: "Nevoeiro",
    48: "Nevoeiro rime",
    51: "Garoa leve",
    53: "Garoa moderada",
    55: "Garoa densa",
    61: "Chuva fraca",
    63: "Chuva moderada",
    65: "Chuva forte",
    71: "Neve leve",
    73: "Neve moderada",
    75: "Neve intensa",
    77: "Grãos de neve",
    80: "Pancadas de chuva",
    81: "Chuva forte",
    82: "Chuva torrencial",
    85: "Pancadas de neve",
    86: "Neve forte",
    95: "Tempestade",
    96: "Tempestade c/ granizo",
    99: "Tempestade severa",
}


def descrever_weather_code(code: int) -> str:
    """Traduz o WMO Weather Code da Open-Meteo para descrição textual legível."""
    return WMO_WEATHER_CODES.get(code, "Tempo instável")


class ServicoClima:
    """Consome a API Open-Meteo com cache local, sem necessidade de API key."""

    def __init__(
        self,
        latitude: float = -23.5505,
        longitude: float = -46.6333,
        cidade: str = "São Paulo",
        intervalo_cache: int = 900,
        timeout: float = 6.0,
    ):
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Latitude inválida ({self.latitude}): deve estar entre -90.0 e 90.0")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"Longitude inválida ({self.longitude}): deve estar entre -180.0 e 180.0")

        self.cidade = str(cidade)
        self.intervalo_cache = int(intervalo_cache)
        self.timeout = float(timeout)

        self._lock = threading.Lock()
        self._ultimo_cache = None
        self._ultimo_fetch_ts = 0.0

    @property
    def url(self) -> str:
        return (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={self.latitude}&longitude={self.longitude}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m"
            f"&timezone=auto"
        )

    def _fazer_requisicao(self) -> dict:
        """Executa a requisição HTTPS com timeout e decodificação JSON."""
        req = urllib.request.Request(
            self.url,
            headers={"User-Agent": "DeskBot-Homelab/2.0"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            corpo = resp.read(65536).decode("utf-8")
            return json.loads(corpo)

    def obter_clima(self, agora_ts: float = None, forcar: bool = False) -> dict:
        """Retorna o clima atual formatado. Usa cache para não sobrecarregar a API."""
        with self._lock:
            if agora_ts is None:
                agora_ts = time.time()

            # Retorna cache ou fallback se dentro da janela de cache / cooldown
            if not forcar and (agora_ts - self._ultimo_fetch_ts < self.intervalo_cache):
                if self._ultimo_cache:
                    return self._ultimo_cache
                return {
                    "temp": 22.0,
                    "apparent_temp": 22.0,
                    "humidity": 50,
                    "condition": "Indisponível",
                    "weather_code": -1,
                    "is_day": 1,
                    "precipitation": 0.0,
                    "wind_speed": 0.0,
                    "city": self.cidade,
                    "updated_at": time.strftime("%H:%M", time.localtime(agora_ts)),
                    "online": False,
                    "error": "Falha ao obter dados meteorológicos",
                }

            try:
                dados_api = self._fazer_requisicao()
                current = dados_api.get("current", {})

                code = int(current.get("weather_code", 0))
                condicao = descrever_weather_code(code)

                dados = {
                    "temp": round(float(current.get("temperature_2m", 22.0)), 1),
                    "apparent_temp": round(float(current.get("apparent_temperature", 22.0)), 1),
                    "humidity": int(current.get("relative_humidity_2m", 50)),
                    "condition": condicao,
                    "weather_code": code,
                    "is_day": int(current.get("is_day", 1)),
                    "precipitation": float(current.get("precipitation", 0.0)),
                    "wind_speed": round(float(current.get("wind_speed_10m", 0.0)), 1),
                    "city": self.cidade,
                    "updated_at": time.strftime("%H:%M", time.localtime(agora_ts)),
                    "online": True,
                }

                self._ultimo_cache = dados
                self._ultimo_fetch_ts = agora_ts
                return dados
            except (URLError, HTTPError, TimeoutError, Exception):
                # Em caso de falha de rede/API, estabelece cooldown de 5 minutos (300s)
                # para evitar chamadas contínuas desnecessárias
                cooldown = min(300, self.intervalo_cache)
                self._ultimo_fetch_ts = agora_ts - (self.intervalo_cache - cooldown)

                # Fallback gracioso: não vaza detalhes internos de erro no payload MQTT
                mensagem_erro = "Falha ao obter dados meteorológicos"
                if self._ultimo_cache:
                    resultado = dict(self._ultimo_cache)
                    resultado["online"] = False
                    resultado["error"] = mensagem_erro
                    return resultado

                return {
                    "temp": 22.0,
                    "apparent_temp": 22.0,
                    "humidity": 50,
                    "condition": "Indisponível",
                    "weather_code": -1,
                    "is_day": 1,
                    "precipitation": 0.0,
                    "wind_speed": 0.0,
                    "city": self.cidade,
                    "updated_at": time.strftime("%H:%M", time.localtime(agora_ts)),
                    "online": False,
                    "error": mensagem_erro,
                }
