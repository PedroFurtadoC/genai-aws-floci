#!/usr/bin/env bash
# Etapa 5: ASG + métrica simulada + alarme -> SNS -> SQS
set -euo pipefail
export AWS_PROFILE=floci
[ "$(aws sts get-caller-identity --query Account --output text)" = "000000000000" ] || { echo "Não é o Floci"; exit 1; }

# Na AWS real use launch template (launch configuration está descontinuada para contas novas).
aws autoscaling create-launch-configuration --launch-configuration-name lc-campo \
  --image-id ami-12345678 --instance-type t3.micro
aws autoscaling create-auto-scaling-group --auto-scaling-group-name asg-campo \
  --launch-configuration-name lc-campo --min-size 1 --max-size 4 --desired-capacity 1 \
  --availability-zones us-east-1a

TOPICO=$(aws sns create-topic --name alerta-cpu --query TopicArn --output text)
FILA_URL=$(aws sqs create-queue --queue-name fila-alertas --query QueueUrl --output text)
FILA_ARN=$(aws sqs get-queue-attributes --queue-url "$FILA_URL" --attribute-names QueueArn \
  --query Attributes.QueueArn --output text)
aws sns subscribe --topic-arn "$TOPICO" --protocol sqs --notification-endpoint "$FILA_ARN"

aws cloudwatch put-metric-alarm --alarm-name cpu-alta-asg-campo \
  --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=AutoScalingGroupName,Value=asg-campo \
  --statistic Average --period 60 --evaluation-periods 3 --datapoints-to-alarm 3 \
  --threshold 80 --comparison-operator GreaterThanThreshold --alarm-actions "$TOPICO"

# Incidente simulado: CPU subindo de 30% para 95%, um ponto por minuto.
for v in 30 35 45 60 72 85 90 95 95; do
  aws cloudwatch put-metric-data --namespace AWS/EC2 --metric-name CPUUtilization \
    --dimensions AutoScalingGroupName=asg-campo --value "$v" --unit Percent
  echo "CPU=$v%"; sleep 60
done

aws cloudwatch describe-alarms --alarm-names cpu-alta-asg-campo --query 'MetricAlarms[0].StateValue'
aws sqs receive-message --queue-url "$FILA_URL" --max-number-of-messages 1
