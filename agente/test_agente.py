"""Testes offline do laço do agente: python -m pytest -q"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
with mock.patch("boto3.client"):
    import agente

AGORA = datetime.now(timezone.utc)


def pontos(valores):
    return {"Datapoints": [{"Timestamp": AGORA - timedelta(minutes=len(valores) - i), "Average": v,
                            "Maximum": v + 2, "SampleCount": 1} for i, v in enumerate(valores)]}


def tool_use(*chamadas):
    return {"stopReason": "tool_use", "output": {"message": {"role": "assistant", "content": [
        {"toolUse": {"toolUseId": f"id{i}", "name": n, "input": a}} for i, (n, a) in enumerate(chamadas)]}}}


def final(texto):
    return {"stopReason": "end_turn", "output": {"message": {"role": "assistant", "content": [{"text": texto}]}}}


class AudFalsa:
    def __init__(self):
        self.eventos = []

    def registrar(self, evento, **d):
        self.eventos.append((evento, d))


def preparar(cw, asg, valores):
    cw.get_metric_statistics.return_value = pontos(valores)
    asg.describe_auto_scaling_groups.return_value = {"AutoScalingGroups": [
        {"MinSize": 1, "MaxSize": 4, "DesiredCapacity": 1, "Instances": []}]}
    asg.describe_scaling_activities.return_value = {"Activities": [{"StartTime": AGORA, "StatusCode": "Successful"}]}


def test_ferramentas_paralelas_em_uma_mensagem_e_datetime_serializado():
    with mock.patch.object(agente, "bedrock") as br, mock.patch.object(agente, "cw") as cw, \
         mock.patch.object(agente, "autoscaling") as asg:
        preparar(cw, asg, [30, 50, 85, 90, 95])
        br.converse.side_effect = [
            tool_use(("ler_metricas", {"minutos": 30}), ("descrever_asg", {}), ("listar_atividades", {})),
            final("ok")]
        assert agente.executar_agente("diag", aprovar=lambda *a: False, auditoria=AudFalsa()) == "ok"
        msgs = br.converse.call_args.kwargs["messages"][:3]  # lista é mutada depois da chamada
        assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
        assert len(msgs[2]["content"]) == 3  # três toolResult na mesma mensagem
        json.dumps(msgs)  # nada de datetime cru
        resumo = msgs[2]["content"][0]["toolResult"]["content"][0]["json"]["resumo"]
        assert resumo["periodos_consecutivos_acima"] == 3


def test_escrita_negada_nao_executa():
    with mock.patch.object(agente, "bedrock") as br, mock.patch.object(agente, "cw") as cw, \
         mock.patch.object(agente, "autoscaling") as asg:
        preparar(cw, asg, [95])
        br.converse.side_effect = [tool_use(("ajustar_capacidade", {"capacidade": 2, "justificativa": "x"})),
                                   final("negado")]
        agente.executar_agente("diag", aprovar=lambda *a: False, auditoria=AudFalsa())
        asg.set_desired_capacity.assert_not_called()


def test_escrita_aprovada_respeita_maximo():
    with mock.patch.object(agente, "bedrock") as br, mock.patch.object(agente, "cw") as cw, \
         mock.patch.object(agente, "autoscaling") as asg:
        preparar(cw, asg, [95, 95, 95])
        br.converse.side_effect = [tool_use(("ajustar_capacidade", {"capacidade": 8, "justificativa": "x"})),
                                   tool_use(("ajustar_capacidade", {"capacidade": 2, "justificativa": "x"})),
                                   final("feito")]
        agente.executar_agente("diag", aprovar=lambda *a: True, auditoria=AudFalsa())
        asg.set_desired_capacity.assert_called_once_with(AutoScalingGroupName="asg-campo",
                                                         DesiredCapacity=2, HonorCooldown=True)


def test_limite_de_iteracoes():
    with mock.patch.object(agente, "bedrock") as br, mock.patch.object(agente, "cw") as cw, \
         mock.patch.object(agente, "autoscaling") as asg:
        preparar(cw, asg, [50])
        br.converse.return_value = tool_use(("descrever_asg", {}))
        aud = AudFalsa()
        assert "Limite" in agente.executar_agente("diag", auditoria=aud)
        assert br.converse.call_count == agente.MAX_ITER and aud.eventos[-1][0] == "limite_iteracoes"
