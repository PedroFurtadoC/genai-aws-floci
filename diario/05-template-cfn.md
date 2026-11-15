# 05-template-cfn

- Cliente: Claude Code (`claude -p`), modelo `claude-sonnet-5-5`
- Servidores MCP ativos: nenhum
- Ferramentas chamadas: 0
- Turnos: 1 · duração: 32.7 s

## Prompt

```
Gere um template CloudFormation em YAML para esta especificação:
1. Região us-east-1, uma zona de disponibilidade, tag Projeto=genai-aws em todos os recursos.
2. VPC 10.0.0.0/16 com DNS habilitado.
3. Sub-rede pública 10.0.1.0/24 com IP público automático e rota 0.0.0.0/0 para um Internet Gateway.
4. Sub-rede privada 10.0.2.0/24 sem rota para a internet e sem NAT Gateway.
5. Security Group "web": entrada somente TCP 80 de 0.0.0.0/0; nenhuma regra de SSH.
6. EC2 t3.micro na sub-rede pública, AMI Amazon Linux 2023 via parâmetro público do SSM, IMDSv2 obrigatório, Apache instalado por UserData.
7. Bucket S3 relatorios-campo: privado, criptografado e versionado.
8. Tabela DynamoDB triagem: chave arquivo (String), sob demanda, criptografada, com PITR.
9. Outputs: IP e URL do servidor, nome do bucket, ARN da tabela, ID da VPC.
10. Nenhum valor fixo que dependa de conta ou região (AMI, ARNs).
```

## Resposta (sem edição; só o caminho local foi omitido)

<invoke name="Write">
<parameter name="file_path">[caminho local omitido]\template.yaml</parameter>
<parameter name="content">AWSTemplateFormatVersion: "2010-09-09"
Description: Infraestrutura genai-aws - VPC, servidor web Apache, bucket S3 e tabela DynamoDB

Parameters:
  AmiId:
    Type: AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>
    Default: /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64
    Description: AMI Amazon Linux 2023 resolvida em tempo de deploy pelo parametro publico do SSM

Rules:
  SomenteUsEast1:
    Assertions:
      - Assert: !Equals [!Ref "AWS::Region", us-east-1]
        AssertDescription: Este template deve ser implantado somente em us-east-1

Resources:
  # ---------- Rede ----------
  Vpc:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - { Key: Name, Value: genai-aws-vpc }
        - { Key: Projeto, Value: genai-aws }

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - { Key: Name, Value: genai-aws-igw }
        - { Key: Projeto, Value: genai-aws }

  GatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref Vpc
      InternetGatewayId: !Ref InternetGateway

  PublicSubnet:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref Vpc
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs ""]
      MapPublicIpOnLaunch: true
      Tags:
        - { Key: Name, Value: genai-aws-publica }
        - { Key: Projeto, Value: genai-aws }

  PrivateSubnet:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref Vpc
      CidrBlock: 10.0.2.0/24
      AvailabilityZone: !Select [0, !GetAZs ""]
      MapPublicIpOnLaunch: false
      Tags:
        - { Key: Name, Value: genai-aws-privada }
        - { Key: Projeto, Value: genai-aws }

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref Vpc
      Tags:
        - { Key: Name, Value: genai-aws-rt-publica }
        - { Key: Projeto, Value: genai-aws }

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: GatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PublicSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet
      RouteTableId: !Ref PublicRouteTable

  # Sem rotas alem da local (implicita): sem internet e sem NAT Gateway
  PrivateRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref Vpc
      Tags:
        - { Key: Name, Value: genai-aws-rt-privada }
        - { Key: Projeto, Value: genai-aws }

  PrivateSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PrivateSubnet
      RouteTableId: !Ref PrivateRouteTable

  # ---------- Seguranca ----------
  WebSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupName: web
      GroupDescription: Permite HTTP (TCP 80) de qualquer origem; sem SSH
      VpcId: !Ref Vpc
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
          Description: HTTP
      Tags:
        - { Key: Name, Value: web }
        - { Key: Projeto, Value: genai-aws }

  # ---------- Computacao ----------
  WebServer:
    Type: AWS::EC2::Instance
    DependsOn: PublicRoute # precisa de saida para a internet para instalar o Apache
    Properties:
      InstanceType: t3.micro
      ImageId: !Ref AmiId
      SubnetId: !Ref PublicSubnet
      SecurityGroupIds:
        - !Ref WebSecurityGroup
      MetadataOptions:
        HttpTokens: required
        HttpEndpoint: enabled
      UserData:
        Fn::Base64: |
          #!/bin/bash
          dnf install -y httpd
          echo "<h1>genai-aws</h1>" > /var/www/html/index.html
          systemctl enable --now httpd
      Tags:
        - { Key: Name, Value: genai-aws-web }
        - { Key: Projeto, Value: genai-aws }

  # ---------- Armazenamento ----------
  # Nomes de bucket S3 sao globais; o sufixo evita colisao sem fixar conta/regiao no template
  ReportsBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub relatorios-campo-${AWS::AccountId}-${AWS::Region}
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
            BucketKeyEnabled: true
      VersioningConfiguration:
        Status: Enabled
      Tags:
        - { Key: Projeto, Value: genai-aws }

  TriagemTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: triagem
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: arquivo
          AttributeType: S
      KeySchema:
        - AttributeName: arquivo
          KeyType: HASH
      SSESpecification:
        SSEEnabled: true
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      Tags:
        - { Key: Projeto, Value: genai-aws }

Outputs:
  ServerPublicIp:
    Description: IP publico do servidor web
    Value: !GetAtt WebServer.PublicIp
  ServerUrl:
    Description: URL do servidor web
    Value: !Sub http://${WebServer.PublicIp}
  BucketName:
    Description: Nome do bucket de relatorios
    Value: !Ref ReportsBucket
  TableArn:
    Description: ARN da tabela DynamoDB triagem
    Value: !GetAtt TriagemTable.Arn
  VpcId:
    Description: ID da VPC
    Value: !Ref Vpc
</parameter>
</invoke>
.
