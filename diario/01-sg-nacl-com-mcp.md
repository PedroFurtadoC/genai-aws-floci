# 01-sg-nacl-com-mcp

- Cliente: Claude Code (`claude -p`), modelo `claude-sonnet-5-5`
- Servidores MCP ativos: aws-docs, aws-knowledge
- Ferramentas chamadas: 4
  - `search_documentation({"search_phrase": "compare security groups and network ACLs VPC", "limit": 5})`
  - `read_documentation({"url": "https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html", "max_length": 8000})`
  - `read_documentation({"url": "https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html", "max_length": 5000})`
  - `read_documentation({"url": "https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html", "max_length": 6000})`
- Turnos: 5 · duração: 19.7 s

## Prompt

```
Explique a diferença entre Security Group e NACL na AWS, citando as páginas da documentação usadas.
```

## Resposta (sem edição)

# Security Group vs. NACL na AWS

Os dois são firewalls da Amazon VPC, mas funcionam em camadas diferentes.

## Resumo das diferenças

| Característica | Security Group | Network ACL (NACL) |
|---|---|---|
| Nível de atuação | Instância (recurso/interface de rede) | Sub-rede |
| Escopo | Todas as instâncias associadas ao SG | Todas as instâncias nas sub-redes associadas |
| Tipo de regra | Somente **allow** | **Allow** e **deny** |
| Avaliação | Avalia todas as regras antes de decidir | Avalia em ordem crescente do número da regra e para na primeira correspondência |
| Tráfego de retorno | Permitido automaticamente (**stateful**) | Precisa ser liberado explicitamente (**stateless**) |

## Pontos adicionais

**Security Groups**
- Você pode associar vários SGs a um mesmo recurso.
- Uma regra pode referenciar outros security groups.
- Não filtram tráfego de DNS da Amazon, DHCP, metadados de instância EC2, Time Sync Service e IPs reservados do roteador da VPC.
- Não têm custo adicional.

**NACLs**
- Cada sub-rede precisa estar associada a exatamente uma NACL. Se você não associar nenhuma, a sub-rede usa a NACL padrão. Uma NACL pode ser associada a várias sub-redes.
- As regras têm numeração de 1 a 32766. A AWS recomenda usar incrementos (10, 100) para poder inserir regras depois.
- São avaliadas quando o tráfego entra ou sai da sub-rede, não no tráfego interno dentro da mesma sub-rede.
- Também não filtram DNS, DHCP, metadados, etc. Elas não bloqueiam requisições ao Route 53 Resolver (para isso, use o DNS Firewall) nem o acesso ao IMDS.
- Não têm custo adicional.

## Quando usar cada um

A documentação recomenda usar **security groups como mecanismo principal** de controle de acesso, por serem mais versáteis (stateful e capazes de referenciar outros SGs). As **NACLs** servem como controle secundário e grosso: para negar um subconjunto específico de tráfego, como "guard rails" de sub-rede ou como defesa em profundidade, caso uma instância seja lançada sem o SG correto. Dá para proteger instâncias só com SGs, e as NACLs são uma camada extra opcional.

## Páginas da documentação usadas

1. **Infrastructure security in Amazon VPC**, seção "Compare security groups and network ACLs" e "Control network traffic": https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html
2. **Control traffic to your AWS resources using security groups**: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html
3. **Control subnet traffic with network access control lists**: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html

A busca inicial também devolveu um resultado do whitepaper "AWS Overview" (https://docs.aws.amazon.com/whitepapers/latest/aws-overview/networking-services.html). Não usei esse resultado, porque ele é genérico e as três páginas do guia da VPC cobrem o assunto com mais detalhe.
