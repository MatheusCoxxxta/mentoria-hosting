# Guia do Aluno — Publicando seu projeto na VPS da mentoria

Este guia te leva do zero até o seu projeto rodando em
`https://SEU-PROJETO.mentoria.sanjacode.space`, com deploy automático a cada
`git push`. Não precisa saber Linux — é só seguir na ordem. Copie e cole os
comandos, trocando o que estiver `ASSIM`.

> **O que vai acontecer, em uma frase:** você dá `git push`, o GitHub monta a
> imagem do seu app, envia pra VPS por SSH, e a VPS sobe seu container atrás de
> um proxy com HTTPS automático. Você nunca acessa a VPS direto.

---

## 0. Antes de começar, você precisa ter

- [ ] Uma conta no **GitHub** e seu projeto num **repositório** lá.
- [ ] Um **`Dockerfile`** no projeto (o que empacota seu app). Veja o §3.
- [ ] Seu app deve **escutar na porta que a variável `PORT` indicar** (ex.: `3000`).
- [ ] Ter recebido do **mentor**:
  - o **nome do seu projeto** (vira o subdomínio). Ex.: `bankacc`.
  - o **endereço da VPS** (um IP). Ex.: `10.00.198.00`.
- [ ] Ter enviado ao mentor a sua **chave pública** (você gera no §4).

Glossário rápido:
- **Secret**: um valor secreto guardado no GitHub (senha, chave). O GitHub
  esconde ele nos logs. Você cadastra em *Settings → Secrets and variables → Actions*.
- **Workflow**: um arquivo `.yml` dentro de `.github/workflows/` que o GitHub
  executa automaticamente (aqui: build + deploy).
- **Container / imagem**: a “caixinha” isolada onde seu app roda. A imagem é o
  molde; o container é a instância rodando.

---

## 1. Visão geral dos arquivos que você vai copiar

Dentro da pasta `template/` da mentoria tem:

```
.github/workflows/
├── deploy.yml   # build + deploy (roda a cada push na main)
├── db.yml       # cria seu banco no Postgres compartilhado (roda 1x, na mão)
└── ops.yml      # operações: ver status, logs, remover (roda na mão)
```

Você copia essa pasta `.github` inteira pra **raiz do seu repositório**.

---

## 2. Copie os workflows pro seu repositório

No seu computador, dentro da pasta do seu projeto:

```bash
# 1) crie a pasta de workflows (o -p não reclama se já existir)
mkdir -p .github/workflows

# 2) copie os 3 arquivos do template da mentoria pra dentro dela
#    (troque CAMINHO/DO/template pelo lugar onde você baixou o template)
cp CAMINHO/DO/template/.github/workflows/*.yml .github/workflows/
```

Se preferir, crie os 3 arquivos na mão pelo próprio site do GitHub
(*Add file → Create new file*, nome `.github/workflows/deploy.yml`, cola o conteúdo).

Ainda **não** dê push — falta configurar (§5 e §6).

---

## 3. Confira seu Dockerfile

Seu app precisa de um `Dockerfile` na raiz (ou na subpasta, se for monorepo).
Exemplo para Node.js:

```dockerfile
FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
EXPOSE 3000
CMD ["node", "app.js"]
```

Duas regras que **não** podem faltar:

1. **Escutar na porta certa.** No código, use a variável de ambiente `PORT`:
   ```js
   const port = process.env.PORT || 3000;
   app.listen(port);
   ```
2. **Não precisa expor porta pública nem configurar HTTPS.** O proxy da VPS
   (Traefik) cuida disso. Seu app só escuta numa porta alta (>1024, ex.: 3000).

---

## 4. Gere sua chave SSH (o “crachá” do deploy)

A chave SSH é um par de arquivos: uma parte **pública** (você entrega ao mentor)
e uma **privada** (fica secreta, vai num secret do GitHub). É assim que o GitHub
prova pra VPS que pode fazer deploy do **seu** projeto — e só dele.

No seu computador (Mac/Linux; no Windows use o Git Bash):

```bash
ssh-keygen -t ed25519 -f mentoria -N "" -C "SEU-PROJETO"
```

Isso cria dois arquivos na pasta atual:
- `mentoria` → chave **privada** (NUNCA compartilhe, não suba no git).
- `mentoria.pub` → chave **pública** (essa você manda pro mentor).

Veja o conteúdo da pública e mande pro mentor (WhatsApp/Discord/etc.):

```bash
cat mentoria.pub
```
Vai aparecer algo como `ssh-ed25519 AAAAC3Nz... SEU-PROJETO`. **O mentor cadastra
essa chave na VPS** e te confirma que seu projeto foi criado.

---

## 5. Cadastre os secrets no GitHub

No seu repositório: **Settings → Secrets and variables → Actions → New repository secret**.
Crie um por um. São **6** (os 3 primeiros valem pra qualquer projeto; os 3 de
banco só se o seu app usa Postgres):

| Nome do secret       | O que é / onde conseguir |
|----------------------|--------------------------|
| `VPS_HOST`           | O IP da VPS que o mentor te passou. Ex.: `45.32.175.10` |
| `VPS_SSH_KEY`        | A **chave privada** inteira. Rode `cat mentoria` e cole **tudo**, incluindo as linhas `-----BEGIN OPENSSH PRIVATE KEY-----` e `-----END OPENSSH PRIVATE KEY-----` |
| `VPS_KNOWN_HOSTS`    | A “identidade” da VPS (evita ataque de impostor). Rode o comando abaixo e cole a linha inteira |
| `DATABASE_USER`      | **O nome do seu projeto** (o mesmo do subdomínio, ex.: `bankacc`). O banco usa esse nome. |
| `DATABASE_NAME`      | **O nome do seu projeto** também — igual ao `DATABASE_USER`. |
| `DATABASE_PASSWORD`  | A senha do **seu** banco. **Você inventa.** Só letras e números, 8 a 64 caracteres (ex.: `Mentoria2026abc`). Guarde-a. |

> **Por que `DATABASE_USER` e `DATABASE_NAME` são o nome do projeto?** O banco é
> compartilhado: quando você roda o workflow **db** (§7), a VPS cria um usuário e
> um database com o **nome do seu projeto**. Então esses dois secrets têm que ser
> exatamente esse nome — senão o app tenta um banco que não existe.

Comando para o `VPS_KNOWN_HOSTS` (troque o IP se for outro):

```bash
ssh-keyscan -t ed25519 45.32.175.10
```
Copie a linha que sair (começa com o IP e `ssh-ed25519 ...`) e cole no secret.

> **Importante:**
> - `VPS_SSH_KEY` é a chave **privada** — vai **só** no secret, nunca no git.
> - Se você recriar a chave, atualize o secret e reenvie a `.pub` pro mentor.
> - Se o mentor reinstalar a VPS, o `VPS_KNOWN_HOSTS` muda — rode o `ssh-keyscan`
>   de novo e atualize o secret.

Precisa de **mais** variáveis no seu app? (ex.: uma chave de API) Crie mais um
secret aqui e replique o padrão no `deploy.yml` (veja o fim do §6).

---

## 6. Ajuste o `deploy.yml` pro seu projeto

O nome do projeto **não** fica no arquivo — ele vem dos secrets (§5) e da chave
SSH. No `deploy.yml` você edita **uma linha só**:

```yaml
env:
  PORT: "3000"   # <-- troque pela porta que o SEU app escuta
```

- `PORT` = a porta que seu app escuta **dentro** do container. Tem que ser a
  mesma que você usa no código (`process.env.PORT`).

**Monorepo?** (vários apps no mesmo repo) Aí ajuste também:
```yaml
      - uses: docker/build-push-action@v6
        with:
          context: ./nome-da-subpasta   # onde está o Dockerfile do seu app
```

Você **não** precisa mexer no resto. O bloco `Deploy` monta o `.env` do container
a partir de valores fixos + os seus secrets:
```
DATABASE_HOST=db          (fixo)
DATABASE_PORT=5432        (fixo)
DATABASE_USER=****        (secret DATABASE_USER = nome do projeto)
DATABASE_NAME=****        (secret DATABASE_NAME = nome do projeto)
DATABASE_PASSWORD=****    (secret DATABASE_PASSWORD)
PORT=<PORT>
```

Tem mais variáveis no seu app? Adicione cada uma como secret (§5) e replique o
padrão nas duas partes do bloco `Deploy`: no `env:` (`MINHA_VAR: ${{ secrets.MINHA_VAR }}`)
e no `printf` (`printf 'MINHA_VAR=%s\n' "$MINHA_VAR"`).

---

## 7. Crie o banco (roda uma vez)

Seu app tem banco? Então rode o workflow **db** uma vez para criar seu usuário e
seu database no Postgres compartilhado:

1. No GitHub, aba **Actions**.
2. Clique no workflow **db** (à esquerda).
3. Botão **Run workflow** → **Run workflow**.

Ele usa o secret `DATABASE_PASSWORD` que você cadastrou. Pode rodar de novo
depois se quiser **trocar a senha** (ele atualiza).

### 7.1 Criar as tabelas (schema)

Criar o banco **não** cria suas tabelas. Duas formas:

- **Recomendado:** seu app roda as próprias *migrations* no start (ex.: um
  `init.sql` que o app executa ao subir, ou uma ferramenta de migration). Assim
  as tabelas nascem com o dono certo (o seu usuário).
- **Alternativa:** peça ao **mentor** para aplicar seu `init.sql` no seu banco.
  (Isso exige acesso de administrador na VPS, que só o mentor tem.)

> Se o app fizer as migrations com a **própria** `DATABASE_URL`, a posse das
> tabelas já fica correta e você evita erro de `permission denied`.

---

## 8. Deploy! (o `git push`)

Agora é só publicar:

```bash
git add .github/workflows
git commit -m "ci: deploy na VPS da mentoria"
git push origin main
```

Acompanhe em **Actions** — o workflow **deploy** vai:
1. montar a imagem do seu app,
2. publicar no GHCR (registro de imagens do GitHub),
3. subir na VPS.

Deu verde? Acesse:
```
https://SEU-PROJETO.mentoria.sanjacode.space
```
Na primeira vez o certificado HTTPS pode levar ~1 minuto pra emitir.

---

## 9. Operação do dia a dia (workflow `ops`)

Aba **Actions → ops → Run workflow**, escolha o comando:

- **ps** — mostra se o container está de pé + uso de CPU/memória.
- **logs** — últimas linhas de log do seu app (use pra investigar erro).
- **rm** — remove o container (o banco é preservado).
- **purge** — remove o container **E apaga o banco** (cuidado, sem volta).

---

## 10. Deu erro? Tabela de sintomas

| O que você vê | Provável causa | O que fazer |
|---|---|---|
| Actions falha no passo **build** | Dockerfile no lugar errado (monorepo) | ajuste `context:` no `deploy.yml` (§6) |
| Página não abre / erro de certificado | HTTPS ainda emitindo | espere ~1 min e recarregue |
| **502 Bad Gateway** | `PORT` do deploy ≠ porta que o app escuta | deixe os dois iguais (§6); confira o código |
| **500** e log diz `relation "..." does not exist` | tabelas não criadas | rode suas migrations / peça o schema ao mentor (§7.1) |
| **500** e log diz `permission denied for table` | tabela criada por outro usuário | as migrations devem rodar com o **seu** usuário do banco |
| **500** e log diz `password authentication failed` | senha do banco divergente | `DATABASE_PASSWORD` (secret) tem que ser a mesma que você usou no workflow **db** |
| **500** e log diz `ECONNREFUSED ... :5432` | app não acha o banco | confira que rodou o workflow **db**; `DATABASE_HOST` deve ser `db` |
| Log com `ECONNREFUSED ... :5672` | seu app tenta RabbitMQ, que não existe na infra | ignore se não usa fila; senão, fale com o mentor |

Para ver o log, use o workflow **ops** com o comando **logs** (§9).

---

## 11. Checklist final

- [ ] `Dockerfile` ok e app escuta em `process.env.PORT`.
- [ ] `.github/workflows/` com os 3 arquivos no repo.
- [ ] Chave SSH gerada; `.pub` enviada e **confirmada** pelo mentor.
- [ ] Secrets: `VPS_HOST`, `VPS_SSH_KEY`, `VPS_KNOWN_HOSTS` (+ `DATABASE_USER`, `DATABASE_NAME`, `DATABASE_PASSWORD` se usa banco).
- [ ] `DATABASE_USER` e `DATABASE_NAME` = **nome do projeto** (igual ao subdomínio).
- [ ] `PORT` ajustado no `deploy.yml`.
- [ ] Workflow **db** rodado uma vez (se usa banco) + tabelas criadas.
- [ ] `git push` → Actions verde → site no ar.

Travou em algum passo? Manda pro mentor **o print do log do Actions** (ou do
`ops → logs`) — é o que mostra o erro de verdade.
