"""Agente de diagnóstico: CloudWatch + Auto Scaling + Bedrock Converse (tool use), com aprovação humana.

Uso: AWS_PROFILE=agente-campo python agente.py "O alarme cpu-alta-asg-campo disparou. Diagnostique."
"""
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ASG = os.environ.get("ASG", "asg-campo")
MODELO = os.environ.get("MODELO", "anthropic.claude-3-haiku-20240307-v1:0")
LOG_GROUP = os.environ.get("LOG_GROUP", "/agente/diagnostico")
MAX_ITER = 6
LIMIAR = 80.0

cw = boto3.client("cloudwatch")
autoscaling = boto3.client("autoscaling")
logs = boto3.client("logs")
# O padrão do boto3 (60 s de leitura, com novas tentativas) estoura com modelo local em CPU e
# reenviaria a mesma inferência; aqui uma tentativa com até 300 s.
bedrock = boto3.client("bedrock-runtime", config=Config(read_timeout=300, retries={"total_max_attempts": 1}))

SISTEMA = f"""Você é um agente de diagnóstico de operações AWS do grupo {ASG}.
Responda em português com três seções: O que aconteceu, Causa provável, Ação recomendada.
Regras obrigatórias:
1. Antes de concluir, chame ler_metricas com janela de pelo menos 15 minutos e use o campo "resumo".
2. Só recomende aumentar a capacidade se periodos_consecutivos_acima >= 3. Com menos evidência, recomende observar.
3. Chame descrever_asg e listar_atividades antes de propor ajuste, para respeitar o máximo e não duplicar uma escala em andamento.
4. Use ajustar_capacidade no máximo uma vez e explique a justificativa. Se a ação for negada, não insista."""

FERRAMENTAS = [
    {"toolSpec": {"name": "ler_metricas",
                  "description": "CPUUtilization média e máxima do grupo por período, com resumo da tendência.",
                  "inputSchema": {"json": {"type": "object", "properties": {
                      "minutos": {"type": "integer", "description": "janela de leitura (15 a 180)"}}}}}},
    {"toolSpec": {"name": "descrever_asg", "description": "Capacidade mínima, máxima, desejada e instâncias do grupo.",
                  "inputSchema": {"json": {"type": "object", "properties": {}}}}},
    {"toolSpec": {"name": "listar_atividades", "description": "Últimas atividades de escala do grupo.",
                  "inputSchema": {"json": {"type": "object", "properties": {}}}}},
    {"toolSpec": {"name": "ajustar_capacidade",
                  "description": "ESCRITA. Altera a capacidade desejada do grupo. Exige aprovação humana.",
                  "inputSchema": {"json": {"type": "object", "properties": {
                      "capacidade": {"type": "integer"}, "justificativa": {"type": "string"}},
                      "required": ["capacidade", "justificativa"]}}}},
]
ESCRITA = {"ajustar_capacidade"}


def ler_metricas(minutos=30):
    minutos = max(15, min(int(minutos), 180))
    fim = datetime.now(timezone.utc)
    r = cw.get_metric_statistics(
        Namespace="AWS/EC2", MetricName="CPUUtilization",
        Dimensions=[{"Name": "AutoScalingGroupName", "Value": ASG}],
        StartTime=fim - timedelta(minutes=minutos), EndTime=fim, Period=60,
        Statistics=["Average", "Maximum", "SampleCount"],
    )
    pontos = sorted(r["Datapoints"], key=lambda p: p["Timestamp"])
    consecutivos = 0
    for p in reversed(pontos):
        if p["Average"] <= LIMIAR:
            break
        consecutivos += 1
    medias = [p["Average"] for p in pontos]
    return {
        "pontos": [{"t": p["Timestamp"], "media": round(p["Average"], 1), "max": round(p["Maximum"], 1)} for p in pontos],
        "resumo": {"n_pontos": len(pontos), "janela_min": minutos,
                   "media_geral": round(sum(medias) / len(medias), 1) if medias else None,
                   "max_geral": max(medias) if medias else None,
                   "periodos_consecutivos_acima": consecutivos, "limiar": LIMIAR},
    }


def descrever_asg():
    g = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[ASG])["AutoScalingGroups"][0]
    return {"min": g["MinSize"], "max": g["MaxSize"], "desejada": g["DesiredCapacity"],
            "instancias": [{"id": i["InstanceId"], "estado": i["LifecycleState"]} for i in g.get("Instances", [])]}


def listar_atividades():
    a = autoscaling.describe_scaling_activities(AutoScalingGroupName=ASG, MaxRecords=10)["Activities"]
    return {"atividades": [{"inicio": x.get("StartTime"), "status": x.get("StatusCode"),
                            "descricao": x.get("Description")} for x in a]}


def ajustar_capacidade(capacidade, justificativa=""):
    g = descrever_asg()
    capacidade = int(capacidade)
    if not g["min"] <= capacidade <= g["max"]:  # validação no código, não só no prompt
        return {"erro": f"capacidade {capacidade} fora do intervalo [{g['min']}, {g['max']}]"}
    autoscaling.set_desired_capacity(AutoScalingGroupName=ASG, DesiredCapacity=capacidade, HonorCooldown=True)
    return {"ok": True, "de": g["desejada"], "para": capacidade}


EXECUTORES = {"ler_metricas": ler_metricas, "descrever_asg": descrever_asg,
              "listar_atividades": listar_atividades, "ajustar_capacidade": ajustar_capacidade}


def para_json(obj):
    """toolResult.json precisa ser JSON puro: datetime vira string ISO."""
    return json.loads(json.dumps(obj, default=str))


class Auditoria:
    """Registra cada passo em um log group do CloudWatch Logs (um stream por execução)."""

    def __init__(self):
        self.stream = f"{datetime.now(timezone.utc):%Y-%m-%d}-{uuid.uuid4().hex[:8]}"
        for criar in (lambda: logs.create_log_group(logGroupName=LOG_GROUP),
                      lambda: logs.create_log_stream(logGroupName=LOG_GROUP, logStreamName=self.stream)):
            try:
                criar()
            except ClientError as e:
                if e.response["Error"]["Code"] != "ResourceAlreadyExistsException":
                    raise

    def registrar(self, evento, **dados):
        linha = json.dumps({"evento": evento, **dados}, default=str, ensure_ascii=False)
        print(linha, file=sys.stderr)
        logs.put_log_events(logGroupName=LOG_GROUP, logStreamName=self.stream,
                            logEvents=[{"timestamp": int(time.time() * 1000), "message": linha}])


def aprovar_no_terminal(nome, entrada):
    return input(f"\n>>> Aprovar {nome} {json.dumps(entrada, ensure_ascii=False)}? [s/N] ").strip().lower() == "s"


def executar_agente(pergunta, aprovar=aprovar_no_terminal, auditoria=None):
    aud = auditoria or Auditoria()
    aud.registrar("inicio", pergunta=pergunta, modelo=MODELO)
    msgs = [{"role": "user", "content": [{"text": pergunta}]}]

    for iteracao in range(1, MAX_ITER + 1):
        resp = bedrock.converse(modelId=MODELO, system=[{"text": SISTEMA}], messages=msgs,
                                toolConfig={"tools": FERRAMENTAS},
                                inferenceConfig={"temperature": 0, "maxTokens": 800})
        msg = resp["output"]["message"]
        msgs.append(msg)

        if resp["stopReason"] != "tool_use":
            texto = "\n".join(b["text"] for b in msg["content"] if "text" in b)
            aud.registrar("resposta_final", iteracao=iteracao, texto=texto)
            return texto

        # Todos os toolResult do turno vão em UMA única mensagem de usuário (exigência da Converse API).
        resultados = []
        for bloco in msg["content"]:
            if "toolUse" not in bloco:
                continue
            uso = bloco["toolUse"]
            nome, entrada = uso["name"], uso.get("input") or {}
            if nome not in EXECUTORES:
                resultado = {"erro": f"ferramenta desconhecida: {nome}"}
            elif nome in ESCRITA and not aprovar(nome, entrada):
                resultado = {"erro": "ação negada pelo operador"}
            else:
                try:
                    resultado = EXECUTORES[nome](**entrada)
                except Exception as e:  # erro vira informação para o modelo, não derruba o laço
                    resultado = {"erro": f"{type(e).__name__}: {e}"}
            resultado = para_json(resultado)
            aud.registrar("ferramenta", iteracao=iteracao, nome=nome, entrada=entrada, resultado=resultado)
            resultados.append({"toolResult": {"toolUseId": uso["toolUseId"], "content": [{"json": resultado}]}})
        msgs.append({"role": "user", "content": resultados})

    aud.registrar("limite_iteracoes", max_iter=MAX_ITER)
    return "Limite de iterações atingido sem conclusão. Escalar para um operador."


if __name__ == "__main__":
    pergunta = " ".join(sys.argv[1:]) or f"O alarme de CPU alta do grupo {ASG} disparou. Diagnostique."
    print(executar_agente(pergunta))
