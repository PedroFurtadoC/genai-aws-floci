# 04-politica-iam

- Cliente: Claude Code (`claude -p`), modelo `claude-sonnet-5-5`
- Servidores MCP ativos: nenhum
- Ferramentas chamadas: 0
- Turnos: 1 · duração: 11.4 s

## Prompt

```
Crie uma política IAM em JSON que permita apenas ler o bucket S3 "relatorios".
```

## Resposta (sem edição)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListarBucketRelatorios",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": "arn:aws:s3:::relatorios"
    },
    {
      "Sid": "LerObjetosRelatorios",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion"
      ],
      "Resource": "arn:aws:s3:::relatorios/*"
    }
  ]
}
```

**Por que dois statements:** `ListBucket` e `GetBucketLocation` se aplicam ao bucket em si (`arn:aws:s3:::relatorios`), enquanto `GetObject` se aplica aos objetos (`arn:aws:s3:::relatorios/*`). Misturar os recursos num só statement não funciona corretamente.

**Notas:**
- Todo o resto é negado implicitamente: sem escrita, exclusão ou acesso a outros buckets.
- `GetObjectVersion` só é útil se o versionamento estiver ativo; pode remover se não precisar.
- Se os objetos usarem criptografia SSE-KMS, também será necessário `kms:Decrypt` na chave correspondente.
- Para restringir a uma pasta específica, use `arn:aws:s3:::relatorios/pasta/*` e adicione uma condição `s3:prefix` no `ListBucket`.
