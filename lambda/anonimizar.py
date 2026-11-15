"""Variante saúde: remove identificadores antes de enviar o texto ao modelo (LGPD, art. 12).

Uso no app.py: texto = anonimizar(texto) logo após o get_object.
Regex é uma primeira barreira; em produção, combine com Amazon Comprehend Medical (DetectPHI) e revisão.
"""
import re

CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
TELEFONE = re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
PRONTUARIO = re.compile(r"\b(prontu[aá]rio|atendimento)\s*(n[ºo.]*\s*)?\d+\b", re.I)
NOME = re.compile(r"\b((?i:paciente|sr\.?|sra\.?))\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+"
                  r"(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)*)")


def anonimizar(texto: str) -> str:
    for padrao, marcador in ((CPF, "[CPF]"), (EMAIL, "[EMAIL]"), (TELEFONE, "[TELEFONE]"),
                             (PRONTUARIO, "[PRONTUARIO]")):
        texto = padrao.sub(marcador, texto)
    return NOME.sub(lambda m: f"{m.group(1)} [NOME]", texto)
