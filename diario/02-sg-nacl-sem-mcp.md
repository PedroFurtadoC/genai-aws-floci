# 02-sg-nacl-sem-mcp

- Cliente: Claude Code (`claude -p`), modelo `claude-sonnet-5-5`
- Servidores MCP ativos: nenhum
- Ferramentas chamadas: 0
- Turnos: 1 · duração: 19.7 s

## Prompt

```
Explique a diferença entre Security Group e NACL na AWS, citando as páginas da documentação usadas.
```

## Resposta (sem edição)

## Security Group vs. NACL

| Característica | Security Group (SG) | Network ACL (NACL) |
|---|---|---|
| **Nível de atuação** | Interface de rede (ENI) da instância/recurso | Sub-rede |
| **Estado** | *Stateful*: a resposta ao tráfego permitido é liberada automaticamente | *Stateless*: entrada e saída são avaliadas separadamente, e é preciso liberar o tráfego de retorno (portas efêmeras) |
| **Tipos de regra** | Apenas `allow` | `allow` e `deny` |
| **Avaliação** | Todas as regras são avaliadas juntas | Em ordem numérica crescente, e a primeira regra que casar é aplicada |
| **Padrão** | Novo SG: nega toda entrada e permite toda saída | NACL padrão da VPC: permite tudo. NACL customizada: nega tudo até você criar regras |
| **Associação** | Um recurso pode ter vários SGs | Uma sub-rede tem exatamente uma NACL, e uma NACL pode atender várias sub-redes |
| **Origem/destino** | Pode referenciar outro SG, além de CIDRs | Apenas CIDRs |

## Quando usar cada um

- **SG** é a defesa principal e mais granular, por exemplo "só o SG do balanceador acessa a porta 8080 do app".
- **NACL** é uma camada extra e grosseira por sub-rede. É a única que permite **bloquear explicitamente** um IP ou CIDR, algo que o SG não faz. Ela só avalia tráfego que entra ou sai da sub-rede, não o tráfego entre instâncias dentro dela.
- O tráfego precisa ser aceito pelas duas camadas. Na prática, usa-se SG para o controle do dia a dia e NACL para bloqueios amplos ou requisitos de conformidade.

## Páginas da documentação citadas

Não abri as páginas nesta sessão. O conteúdo acima vem do meu conhecimento prévio da documentação oficial da AWS, e as URLs abaixo estão de memória, então vale conferir se continuam válidas:

1. *Control traffic to your AWS resources using security groups*: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html
2. *Control subnet traffic with network access control lists*: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html
3. *Compare security groups and network ACLs*, seção do guia "Infrastructure security in Amazon VPC": https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html

Se quiser, posso buscar essas páginas e confirmar cada ponto da tabela contra o texto atual.
