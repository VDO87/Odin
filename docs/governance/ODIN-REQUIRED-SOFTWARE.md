# ODIN-REQUIRED-SOFTWARE
## Projeto Odin

**Versão:** 0.1  
**Estado:** Baseline inicial de setup  
**Tipo de documento:** Requisitos de software e bootstrap  
**Objetivo:** Listar o software necessário para o Odin funcionar e descrever como preparar o ambiente local de desenvolvimento e a camada opcional de memória auxiliar.

---

## 1. Finalidade do documento

Este documento responde a uma necessidade prática:

- que software base é obrigatório;
- que software é opcional;
- o que é instalado pelo `pyproject.toml`;
- o que precisa de existir no sistema operativo;
- que scripts usar para verificar e preparar o ambiente.

---

## 2. Software obrigatório

### 2.1 Sistema base
- `bash`
- `git`
- `python3` 3.12 ou superior
- `python3-venv`
- `pip`
- `sqlite3`

### 2.2 Tooling Python do projeto
Instalado via `pyproject.toml` extras:
- `pytest`
- `ruff`
- `mypy`

---

## 3. Software opcional

### 3.1 Memória auxiliar
- `mempalace` 3.0.0 ou superior

Observação:
- MemPalace é opcional e funciona como sidecar de memória advisory;
- não é requisito para o runtime seguro do Odin;
- quando instalado, traz as dependências Python necessárias do próprio pacote.

### 3.2 Ferramentas úteis mas não mandatórias
- editor com suporte a Python/TOML/Markdown
- terminal com suporte a scripts `bash`

---

## 4. Ficheiros de setup já existentes no projeto

- `INSTALL_ODIN.sh`
- `scripts/install_ubuntu_server.sh`
- `pyproject.toml`
- `config/examples/odin.example.toml`
- `scripts/check_prereqs.sh`
- `scripts/bootstrap_dev.sh`

---

## 5. Instalador automático para Ubuntu Server

Para o caso de uso de Ubuntu Server, faz sentido ter um instalador controlado, porque o alvo é conhecido e os pacotes base são previsíveis.

O projeto passa a ter:

1. um documento que explica os requisitos;
2. um instalador específico para Ubuntu Server;
3. scripts separados para check e bootstrap.

O instalador:
- instala os pacotes de sistema necessários;
- cria a venv;
- instala dependências Python;
- cria a configuração local inicial;
- garante a árvore de runtime necessária.

Regra:
- o instalador automático é suportado para **Ubuntu Server 24.04+**;
- fora desse alvo, o fluxo suportado continua a ser `check_prereqs.sh` + `bootstrap_dev.sh`.

---

## 6. Fluxo recomendado

### 6.1 Verificar pré-requisitos

```bash
./scripts/check_prereqs.sh
```

### 6.2 Instalação automática em Ubuntu Server

```bash
./INSTALL_ODIN.sh
```

### 6.3 Instalação com profile explícito

```bash
./INSTALL_ODIN.sh --profile standard
./INSTALL_ODIN.sh --profile full
```

### 6.4 Instalação automática sem memória auxiliar

```bash
./INSTALL_ODIN.sh --profile full --without-memory
```

### 6.5 Preparar ambiente manualmente

```bash
./scripts/bootstrap_dev.sh
```

### 6.6 Preparar ambiente manualmente com memória auxiliar

```bash
./scripts/bootstrap_dev.sh --with-memory
```

---

## 7. Regra obrigatória

O Odin deve continuar operacional no seu modo seguro mesmo sem MemPalace instalado.  
MemPalace acelera recall e aprendizagem assistida, mas não é dependência autoritativa.

---

## 8. Conclusão

Este documento fecha a parte prática do setup:
- o que tens de instalar;
- o que o projeto já consegue instalar por si no espaço Python;
- e o que fica opcional para memória auxiliar.
