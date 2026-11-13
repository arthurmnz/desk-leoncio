"""Cálculo do Ciclo Circadiano do DeskBot.

Funções puras e sem dependências externas para determinar os ritmos biológicos,
limites de energia, taxas de recuperação e drenagem ao longo do dia.
"""


def clamp(v):
    """Restringe um valor float ao intervalo [0.0, 1.0]."""
    return max(0.0, min(1.0, v))


def fator_circadiano(hora, minuto=0):
    """Calcula os parâmetros da curva circadiana para um determinado momento do dia.

    Retorna um dicionário com:
      - fase: identificador ('madrugada', 'manha', 'slump_tarde', 'tarde_noite', 'pre_sono')
      - label: nome descritivo para logs e observabilidade
      - teto_energia: limite superior biológico da energia (0.35 a 1.0)
      - taxa_drenagem: multiplicador de gasto de energia (ex: 1.6x na madrugada)
      - taxa_recuperacao: multiplicador de recuperação no descanso (ex: 1.3x de manhã, 0.5x de madrugada)
      - tempo_para_dormir: tempo limite (s) sem atividade até o bot adormecer
      - limiar_tedio: sensibilidade ao tédio (menor valor = fica entediado mais fácil)
    """
    t = (hora % 24) + (minuto / 60.0)

    # 1. Madrugada (00h00 - 05h59): Ritmo biológico mínimo
    if 0.0 <= t < 6.0:
        # Teto de energia baixo: vale de 0.35 entre 03:00 e 04:30
        if t < 3.0:
            teto = 0.45 - (t / 3.0) * 0.10
        elif t < 4.5:
            teto = 0.35
        else:
            teto = 0.35 + ((t - 4.5) / 1.5) * 0.10

        return {
            "fase": "madrugada",
            "label": "Madrugada",
            "teto_energia": clamp(round(teto, 3)),
            "taxa_drenagem": 1.6,       # Drenagem acelerada quando o usuário força a barra
            "taxa_recuperacao": 0.5,    # Recuperação lenta de madrugada acordado
            "tempo_para_dormir": 150.0, # Apaga rápido se idle/ausente (~2.5 min)
            "limiar_tedio": 0.5,
        }

    # 2. Manhã / Despertar (06h00 - 11h59): Disposição em ascensão
    if 6.0 <= t < 12.0:
        if t < 8.5:
            teto = 0.45 + ((t - 6.0) / 2.5) * 0.55
        else:
            teto = 1.0

        return {
            "fase": "manha",
            "label": "Manhã / Despertar",
            "teto_energia": clamp(round(teto, 3)),
            "taxa_drenagem": 1.0,
            "taxa_recuperacao": 1.3,    # Recuperação matinal revigorante e mais ágil
            "tempo_para_dormir": 600.0, # 10 minutos
            "limiar_tedio": 0.6,
        }

    # 3. Slump pós-almoço (12h00 - 14h29): Moleza digestiva / circadiana
    if 12.0 <= t < 14.5:
        if t < 12.5:
            teto = 1.0 - ((t - 12.0) / 0.5) * 0.15
        elif t < 14.0:
            teto = 0.85
        else:
            teto = 0.85 + ((t - 14.0) / 0.5) * 0.15

        return {
            "fase": "slump_tarde",
            "label": "Slump pós-almoço",
            "teto_energia": clamp(round(teto, 3)),
            "taxa_drenagem": 1.15,
            "taxa_recuperacao": 0.7,    # Moleza digestiva, descanso mais sonolento
            "tempo_para_dormir": 420.0, # 7 minutos
            "limiar_tedio": 0.40,       # Fica entediado com mais facilidade se idle
        }

    # 4. Entardecer / Noite produtiva (14h30 - 21h59): Ritmo de pico produtivo
    if 14.5 <= t < 22.0:
        return {
            "fase": "tarde_noite",
            "label": "Tarde / Noite produtiva",
            "teto_energia": 1.0,
            "taxa_drenagem": 1.0,
            "taxa_recuperacao": 1.0,
            "tempo_para_dormir": 600.0, # 10 minutos
            "limiar_tedio": 0.6,
        }

    # 5. Pré-sono / Desaceleração (22h00 - 23h59): Fadiga diária acumulada
    teto = 1.0 - ((t - 22.0) / 2.0) * 0.55
    return {
        "fase": "pre_sono",
        "label": "Pré-sono / Desaceleração",
        "teto_energia": clamp(round(teto, 3)),
        "taxa_drenagem": 1.25,
        "taxa_recuperacao": 0.8,
        "tempo_para_dormir": 300.0, # 5 minutos
        "limiar_tedio": 0.55,
    }


calcular_ritmo_circadiano = fator_circadiano
