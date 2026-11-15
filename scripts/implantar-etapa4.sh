#!/usr/bin/env bash
# Etapa 4: S3 -> Lambda -> Bedrock -> DynamoDB no Floci
set -euo pipefail
export AWS_PROFILE=floci
[ "$(aws sts get-caller-identity --query Account --output text)" = "000000000000" ] || { echo "Não é o Floci"; exit 1; }

aws s3 mb s3://relatorios-campo
aws dynamodb create-table --table-name triagem \
  --attribute-definitions AttributeName=arquivo,AttributeType=S \
  --key-schema AttributeName=arquivo,KeyType=HASH --billing-mode PAY_PER_REQUEST
aws iam create-role --role-name triagem-lambda --assume-role-policy-document file://iam/confianca-lambda.json
aws iam put-role-policy --role-name triagem-lambda --policy-name triagem-minimo \
  --policy-document file://iam/politica-lambda-triagem.json

(cd lambda && rm -f ../funcao.zip && zip -q ../funcao.zip app.py)
aws lambda create-function --function-name triagem --runtime python3.12 \
  --handler app.handler --zip-file fileb://funcao.zip --timeout 120 --memory-size 256 \
  --role arn:aws:iam::000000000000:role/triagem-lambda \
  --environment 'Variables={TABELA=triagem}'

# Na AWS real este passo é obrigatório antes da notificação (o Floci não exige):
aws lambda add-permission --function-name triagem --statement-id s3-invoke \
  --action lambda:InvokeFunction --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::relatorios-campo || true

aws s3api put-bucket-notification-configuration --bucket relatorios-campo \
  --notification-configuration '{"LambdaFunctionConfigurations":[{"LambdaFunctionArn":"arn:aws:lambda:us-east-1:000000000000:function:triagem","Events":["s3:ObjectCreated:*"]}]}'

for f in relatorios/*.txt; do aws s3 cp "$f" s3://relatorios-campo/; done
echo "Aguarde a 1ª invocação (baixa a imagem do runtime) e rode:"
echo "  aws dynamodb scan --table-name triagem --output table"
echo "  aws logs tail /aws/lambda/triagem --follow"
