"""Inventário de buckets S3, tabelas DynamoDB e usuários IAM.

Não fixa endpoint no código: usa o perfil (AWS_PROFILE=floci). Antes de qualquer chamada,
confirma que a conta é a fictícia do Floci, para nunca listar (ou alterar) uma conta real por engano.
"""
import sys

import boto3

CONTA_FLOCI = "000000000000"

sessao = boto3.Session()
conta = sessao.client("sts").get_caller_identity()["Account"]
if conta != CONTA_FLOCI:
    sys.exit(f"ABORTADO: conta {conta} não é o Floci. Rode: export AWS_PROFILE=floci")

print(f"Conta {conta} | perfil {sessao.profile_name} | região {sessao.region_name}\n")

print("Buckets S3:")
for b in sessao.client("s3").list_buckets().get("Buckets", []):
    print(f"  - {b['Name']}")

print("Tabelas DynamoDB:")
for pagina in sessao.client("dynamodb").get_paginator("list_tables").paginate():
    for t in pagina["TableNames"]:
        print(f"  - {t}")

print("Usuários IAM:")
for pagina in sessao.client("iam").get_paginator("list_users").paginate():
    for u in pagina["Users"]:
        print(f"  - {u['UserName']}  ({u['Arn']})")
