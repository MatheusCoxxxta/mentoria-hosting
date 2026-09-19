#!/usr/bin/env python3
"""Lê o corpo de uma issue do formulário "Novo projeto" e valida os campos.

O corpo da issue é texto controlado por quem abriu a issue: NUNCA é interpolado
em shell. Entra por variável de ambiente (ISSUE_BODY), sai validado em arquivo.

Saídas:
  - <payload>  : 2 linhas — "<projeto>\n<ssh-ed25519> <base64>\n" (stdin do gate)
  - GITHUB_OUTPUT: projeto=<projeto>  (já validado contra ^[a-z][a-z0-9-]*$)
Em caso de erro: mensagem amigável em GITHUB_OUTPUT (erro=...) e exit 1.
"""
import base64
import os
import re
import sys

PROJ_RE = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*\Z")
B64_RE = re.compile(r"[A-Za-z0-9+/]+={0,2}\Z")
# blob de uma chave ed25519: len("ssh-ed25519")=11 + nome + len(32) + 32 bytes
ED25519_BLOB = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20"

L_PROJETO = "Nome do projeto"
L_CHAVE = "Chave pública SSH (ed25519)"


def secoes(body: str) -> dict:
    """Quebra o markdown gerado pelo issue form em {rótulo: valor}.

    A PRIMEIRA ocorrência de cada rótulo vence. Isso importa: o aluno pode
    escrever `### Nome do projeto` dentro de um campo de texto livre e, se a
    última vencesse, o mentor aprovaria olhando um valor e a VPS cadastraria
    outro. Como o form emite os campos em ordem fixa e o campo de nome é
    `type: input` (uma linha, sem `###` possível), a primeira é sempre a real.
    """
    out, atual, buf = {}, None, []

    def fecha():
        if atual is not None and atual not in out:
            out[atual] = "\n".join(buf).strip()

    for line in body.replace("\r\n", "\n").split("\n"):
        if line.startswith("### "):
            fecha()
            atual, buf = line[4:].strip(), []
        elif atual is not None:
            buf.append(line)
    fecha()
    return out


def sem_cerca(valor: str) -> str:
    """Campo com `render: text` vem dentro de ```...```; tira a cerca."""
    linhas = valor.split("\n")
    if linhas and linhas[0].startswith("```"):
        linhas = linhas[1:]
    while linhas and linhas[-1].strip() == "```":
        linhas = linhas[:-1]
    return "\n".join(linhas).strip()


def uma_linha(valor: str, limite: int = 200) -> str:
    """Achata para uma linha só. O corpo da issue é editável à mão pelo autor:
    um `\\n` num valor viraria uma linha extra no GITHUB_OUTPUT, ou seja,
    output arbitrário injetado no workflow."""
    return " ".join(valor.split())[:limite]


def escrever_output(chave: str, valor: str) -> None:
    saida = os.environ.get("GITHUB_OUTPUT")
    if saida:
        with open(saida, "a", encoding="utf-8") as fh:
            fh.write(f"{chave}={uma_linha(valor)}\n")


def falhar(msg: str) -> None:
    escrever_output("erro", msg)
    print(f"erro: {uma_linha(msg, 400)}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    destino = sys.argv[1] if len(sys.argv) > 1 else "payload.txt"
    campos = secoes(os.environ.get("ISSUE_BODY", ""))

    projeto = sem_cerca(campos.get(L_PROJETO, ""))
    if not (PROJ_RE.match(projeto) and len(projeto) <= 30):
        falhar(
            f"nome de projeto inválido: `{projeto[:60]}`. "
            "Use só letras minúsculas, números e hífen, começando por letra "
            "(até 30 caracteres). Ex.: `meu-app`."
        )

    chave = " ".join(sem_cerca(campos.get(L_CHAVE, "")).split())
    if "BEGIN OPENSSH PRIVATE KEY" in chave or "PRIVATE KEY" in chave:
        falhar(
            "você colou a chave **PRIVADA**. Ela está comprometida: apague esta "
            "issue, gere um par novo (`ssh-keygen`) e abra outra issue com o "
            "conteúdo de `mentoria.pub`."
        )

    partes = chave.split(" ")
    if len(partes) < 2 or partes[0] != "ssh-ed25519":
        falhar(
            "a chave precisa ser ed25519 e começar com `ssh-ed25519 `. "
            "Gere com `ssh-keygen -t ed25519 -f mentoria -N \"\" -C \"SEU-PROJETO\"` "
            "e cole a saída de `cat mentoria.pub`."
        )

    tipo, dados = partes[0], partes[1]
    if not B64_RE.match(dados):
        falhar("a parte base64 da chave tem caracteres inválidos — cole a linha inteira, sem quebras.")
    try:
        bruto = base64.b64decode(dados, validate=True)
    except Exception:
        falhar("não consegui decodificar a chave — cole a linha inteira de `mentoria.pub`.")
    if len(bruto) != 51 or not bruto.startswith(ED25519_BLOB):
        falhar("isso não é uma chave pública ed25519 válida. Confira o conteúdo de `mentoria.pub`.")

    with open(destino, "w", encoding="utf-8") as fh:
        fh.write(f"{projeto}\n{tipo} {dados}\n")

    escrever_output("projeto", projeto)
    print(f"ok: projeto={projeto} chave={tipo} {dados[:16]}…")


if __name__ == "__main__":
    main()
