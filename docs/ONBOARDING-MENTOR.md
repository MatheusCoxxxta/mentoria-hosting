# Onboarding automático — guia do mentor

Cadastro de projeto novo sem SSH na mão: o aluno abre uma issue com nome do
projeto + chave pública, você põe a label `aprovado`, uma Action cadastra na VPS
e comenta os próximos passos na própria issue.

## Como funciona

```
aluno abre issue (form "Novo projeto na VPS")
        │
        ▼
mentor põe a label `aprovado`          ← ESTE é o controle de acesso
        │
        ▼
.github/workflows/onboarding.yml
   ├─ confere o aprovador (label exige permissão; + vars.MENTORES se definida)
   ├─ parse-issue.py valida nome e chave (nunca passa por shell)
   └─ ssh onboarder@VPS  < "projeto\nssh-ed25519 <base64>"
                │
                ▼
        mentoria-onboard-gate   (forced command, sem argumentos, stdin só)
                │ sudo -n
                ▼
        mentoria-add-projeto  → slice + authorized_keys do deployer + /opt/mentoria/data
        │
        ▼
robô comenta na issue, aplica `provisionado` e fecha
```

## Por que é seguro

| Preocupação | Por quê não é problema |
|---|---|
| "A chave vaza na issue pública" | É a chave **pública**. Existe para ser distribuída; não abre nada sozinha. O parser recusa, com aviso em destaque, qualquer coisa que contenha `PRIVATE KEY`. |
| "Qualquer um pede um projeto" | O workflow só roda em `issues: [labeled]` com `aprovado`. Aplicar label exige permissão triage/write no repo — o autor da issue não consegue. Opcionalmente restrinja mais com a variável `MENTORES`. |
| "O corpo da issue é texto hostil" | Nunca entra num `run:` via `${{ }}` (isso seria *script injection*). Vai por `env:` e é validado em Python: regex do nome, base64 decodificado e conferido como blob ed25519 de 51 bytes. Depois é revalidado no gate em bash e de novo no `mentoria-add-projeto`. |
| "E se a chave da CI vazar?" | Ela é do usuário `onboarder`, preso a `command="…/mentoria-onboard-gate",restrict`. Sem shell, sem port-forward, sem `SSH_ORIGINAL_COMMAND`. O portador só consegue cadastrar projeto novo — não vê, não altera e não remove projeto existente. `sudo` só libera `mentoria-add-projeto`. |
| "O robô expõe o IP da VPS" | Não expõe: `VPS_HOST` não entra no comentário da issue nem em nenhum `echo`. O aluno recebe o IP de você, em particular. (Nos logs do Actions ele já sai mascarado por ser secret.) |

## Instalação (uma vez)

**1. Gere o par da CI** (na sua máquina, não na VPS):

```bash
ssh-keygen -t ed25519 -f onboarding-ci -N "" -C "onboarding-ci"
```

**2. Registre a pública na VPS** — o `setup.sh` aceita como 3º argumento e é
idempotente:

```bash
scp onboarding-ci.pub root@SEU-IP:/tmp/
ssh root@SEU-IP
cd /caminho/do/repo/vps
sudo ./setup.sh mentoria.sanjacode.space voce@email.com "$(cat /tmp/onboarding-ci.pub)"
rm /tmp/onboarding-ci.pub
```

**3. Secrets no repo da mentoria** (*Settings → Secrets and variables → Actions*):

| Secret | Valor |
|---|---|
| `VPS_HOST` | IP da VPS |
| `VPS_ONBOARD_KEY` | conteúdo de `cat onboarding-ci` (a **privada**) |
| `VPS_KNOWN_HOSTS` | saída de `ssh-keyscan -t ed25519 SEU-IP` |

Depois apague a privada da sua máquina (`rm onboarding-ci`) — ela só precisa
existir no secret. Precisou rotacionar? Gere outro par, rode o passo 2 de novo e
tire a linha antiga de `/home/onboarder/.ssh/authorized_keys`.

**4. (Opcional) Variável `MENTORES`** em *Settings → Variables → Actions*:
`fulano,ciclana`. Se estiver vazia, vale só a permissão de label.

**5. Teste** abrindo você mesmo uma issue pelo formulário e aprovando.

## Uso no dia a dia

1. Chega a issue com label `novo-projeto`.
2. Confira: o nome do projeto está livre? O aluno é da turma? A chave é `ssh-ed25519`?
3. Label `aprovado`.
4. Deu ✅ no comentário → pronto. Deu ❌ → o robô já explicou o que corrigir na
   issue e marcou `invalido`; o aluno edita o corpo e você reaplica `aprovado`.

**Nome já cadastrado** falha com `projeto já cadastrado` (vem do
`mentoria-add-projeto`). Peça outro nome, ou remova o antigo antes:

```bash
sudo mentoria-del-projeto <projeto>            # preserva o banco
sudo mentoria-del-projeto <projeto> --purge-db # apaga o banco também
```

Remoção continua sendo manual e por SSH, de propósito: é destrutiva e não deve
ficar a um clique de label.
