"""Projeção de custo da triagem (Etapa 6).

Sem argumentos: lê os tokens reais gravados na tabela triagem do Floci.
Com --tin/--tout: usa médias informadas (útil antes de medir).
Preços on-demand us-east-1 conferidos na AWS Price List (offers AmazonBedrock, AmazonBedrockFoundationModels
e AmazonEC2) em 14/11/2026; o Haiku 4.5 usa o perfil de inferência global (regional: 1,10 / 5,50).
"""
import argparse

PRECOS = {  # (entrada, saída) em USD por 1M tokens
    "Amazon Nova Micro": (0.035, 0.14),
    "Claude Haiku 4.5": (1.00, 5.00),
}
LAMBDA_GB_S, LAMBDA_REQ = 0.0000166667, 0.20 / 1_000_000
GPU_HORA = 0.526  # g4dn.xlarge on-demand, us-east-1
HORAS_MES = 730


def medias_do_floci():
    import boto3
    itens, kw = [], {}
    tab = boto3.resource("dynamodb").Table("triagem")
    while True:
        r = tab.scan(ProjectionExpression="tokens_in, tokens_out, latencia_ms", **kw)
        itens += r["Items"]
        if "LastEvaluatedKey" not in r:
            break
        kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]
    n = len(itens)
    media = lambda k: sum(float(i[k]) for i in itens) / n
    return media("tokens_in"), media("tokens_out"), media("latencia_ms") / 1000, n


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tin", type=float)
    p.add_argument("--tout", type=float)
    p.add_argument("--duracao-s", type=float, default=2.0, help="duração média da Lambda na AWS real")
    p.add_argument("--por-dia", type=int, default=500)
    a = p.parse_args()

    if a.tin is None:
        tin, tout, lat, n = medias_do_floci()
        print(f"Medido no Floci: {n} relatórios, latência média local {lat:.1f} s")
    else:
        tin, tout = a.tin, a.tout
    mes = a.por_dia * 30
    lam = mes * a.duracao_s * 0.25 * LAMBDA_GB_S + mes * LAMBDA_REQ  # 256 MB, sem free tier
    print(f"Média: {tin:.0f} tokens de entrada, {tout:.0f} de saída | {mes:,} relatórios/mês\n")
    print(f"{'Modelo':<20}{'US$/relatório':>15}{'US$/mês IA':>12}{'+Lambda':>10}{'Equilíbrio GPU (rel./dia)':>28}")
    for nome, (pin, pout) in PRECOS.items():
        unit = tin / 1e6 * pin + tout / 1e6 * pout
        eq = GPU_HORA * HORAS_MES / unit / 30
        print(f"{nome:<20}{unit:>15.6f}{unit * mes:>12.2f}{unit * mes + lam:>10.2f}{eq:>28,.0f}")
    print(f"\nLambda isolada (256 MB, {a.duracao_s:.0f} s): US$ {lam:.2f}/mês (coberta pelo free tier)")
    print(f"EC2 g4dn.xlarge 24x7: US$ {GPU_HORA * HORAS_MES:.2f}/mês")


if __name__ == "__main__":
    main()
