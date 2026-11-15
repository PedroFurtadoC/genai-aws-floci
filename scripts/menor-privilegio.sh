#!/usr/bin/env bash
# Etapa 2: menor privilégio real. Pré-requisito: Floci com FLOCI_SERVICES_IAM_ENFORCEMENT_ENABLED=true
set -euo pipefail
export AWS_PROFILE=floci
[ "$(aws sts get-caller-identity --query Account --output text)" = "000000000000" ] || { echo "Não é o Floci"; exit 1; }

aws iam create-user --user-name leitor-relatorios
aws iam put-user-policy --user-name leitor-relatorios --policy-name leitura-relatorios \
  --policy-document file://iam/politica-leitura-relatorios.json
read -r KEY SECRET < <(aws iam create-access-key --user-name leitor-relatorios \
  --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text)

# Credenciais do usuário restrito só neste subshell (sem perfil, endpoint explícito)
(
  unset AWS_PROFILE
  export AWS_ACCESS_KEY_ID=$KEY AWS_SECRET_ACCESS_KEY=$SECRET AWS_DEFAULT_REGION=us-east-1
  export AWS_ENDPOINT_URL=http://localhost:4566
  echo "== get-object (deve PASSAR)"
  aws s3api get-object --bucket relatorios --key inspecao-001.txt /tmp/inspecao.txt && cat /tmp/inspecao.txt
  echo "== put-object (deve FALHAR com AccessDenied)"
  echo teste > /tmp/x.txt
  if aws s3api put-object --bucket relatorios --key x.txt --body /tmp/x.txt; then
    echo "ERRO: put passou, a aplicação de IAM não está ligada"; exit 1
  else
    echo "OK: put negado"
  fi
)
