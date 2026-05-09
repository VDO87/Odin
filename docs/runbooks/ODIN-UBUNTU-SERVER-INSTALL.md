# ODIN-UBUNTU-SERVER-INSTALL
## Projeto Odin

**Versão:** 0.1  
**Estado:** instalação com profiles operacionais e validação de config  
**Tipo de documento:** Runbook de instalação  
**Objetivo:** Descrever o fluxo suportado de instalação automática do Odin em Ubuntu Server.

---

## 1. Finalidade

Este runbook descreve o fluxo simples e suportado para instalar o Odin em Ubuntu Server com um único ficheiro de entrada.

O ficheiro principal é:

- `INSTALL_ODIN.sh`

---

## 2. O que o instalador faz

O instalador:
- valida que o sistema é Ubuntu;
- valida o profile pedido e a compatibilidade com memória auxiliar;
- instala os pacotes base com `apt`;
- por omissão cria instalação isolada em `$HOME/odin-runtime` (com `config/`, `runtime/`, `.venv/`, `bin/`);
- garante a árvore `runtime/` dentro da pasta de instalação;
- cria `config/odin.local.toml` a partir do exemplo do profile pedido, apenas quando o ficheiro ainda não existe;
- cria a `.venv` dentro da pasta de instalação;
- instala dependências Python;
- valida o config resultante com `odin-validate-config`;
- só instala MemPalace quando o profile é `full` e a memória auxiliar está ativa;
- gera `install-manifest.json` com metadados de rastreio;
- instala a unidade `systemd` `odin-core.service` apenas em `--in-place` (ou ignora com `--skip-systemd`).

Notas operacionais importantes:
- profile por omissão do instalador: `lite`;
- modo por omissão: instalação isolada em `$HOME/odin-runtime`;
- com `--profile full` e sem flag de memória, a instalação assume memória auxiliar ativa por defeito;
- se `config/odin.local.toml` já existir, o instalador preserva o ficheiro atual (não faz overwrite de profile).

---

## 3. Execução recomendada

### 3.1 Instalação padrão

```bash
./INSTALL_ODIN.sh
```

### 3.2 Instalação com profile explícito

```bash
./INSTALL_ODIN.sh --profile standard
./INSTALL_ODIN.sh --profile full
```

### 3.3 Instalação sem memória auxiliar

```bash
./INSTALL_ODIN.sh --profile full --without-memory
```

### 3.4 Dry-run

```bash
./INSTALL_ODIN.sh --dry-run --profile lite
```

### 3.5 Instalação sem apt

```bash
./INSTALL_ODIN.sh --skip-apt
```

### 3.6 Pasta de instalação isolada explícita

```bash
./INSTALL_ODIN.sh --install-root "$HOME/odin-instances/lab-01"
```

### 3.7 Instalação in-place (layout legado do repositório)

```bash
./INSTALL_ODIN.sh --in-place
```

### 3.8 Instalação sem systemd

```bash
./INSTALL_ODIN.sh --skip-systemd
```

### 3.9 Perfis suportados

- `lite` — profile por defeito; sem `LEARN`, shadow mode, memória auxiliar e surface LEARN no `DASH`; no `MARKET`, scope mínimo (`1` instrumento/`1` feed), `news_guard` desligado e enriquecimento pesado desligado
- `standard` — operação normal sem `LEARN`, com `DASH` standard e sem envelope mínimo forçado do `MARKET`
- `full` — expõe `LEARN`, shadow mode e pode ativar memória auxiliar

---

## 4. Regra de arquitetura

Mesmo quando instalado com MemPalace:
- o `CORE` continua autoridade única de estado;
- a persistência crítica continua em `SDS-110`;
- a memória auxiliar nunca governa risco, execução ou recovery.

---

## 5. Observação prática

Em Ubuntu Server puro, o uso normal é executar o ficheiro pelo terminal.  
Se a pasta for aberta num ambiente com file manager, o `INSTALL_ODIN.sh` também pode ser executado como script.

---

## 6. Pós-instalação

Após instalação:

```bash
$HOME/odin-runtime/bin/start_odin.sh
```

Teste local da consola (recomendado para validação de dashboard/API):

```bash
$HOME/odin-runtime/bin/start_operator_console.sh
```

Nota:
- para testes da consola, evitar correr `start_odin.sh` e `start_operator_console.sh` ao mesmo tempo.

Para gestão via `systemd`:

```bash
sudo systemctl start odin-core.service
sudo systemctl status odin-core.service
sudo journalctl -u odin-core.service -n 100 --no-pager
```

Ficheiros e diretórios principais:
- `$HOME/odin-runtime/config/odin.local.toml`
- `$HOME/odin-runtime/.venv/`
- `$HOME/odin-runtime/bin/start_odin.sh`
- `$HOME/odin-runtime/bin/start_operator_console.sh`
- `$HOME/odin-runtime/install-manifest.json`
- `systemd/odin-core.service.template`
- `$HOME/odin-runtime/runtime/logs/`
- `$HOME/odin-runtime/runtime/state/`
- `$HOME/odin-runtime/runtime/backups/`
- `$HOME/odin-runtime/runtime/memory/` quando o profile/instalação ativar memória auxiliar

Purge seguro da instalação isolada:
```bash
ODIN_HOME="$HOME/odin-runtime" scripts/odin_purge.sh --dry-run
ODIN_HOME="$HOME/odin-runtime" scripts/odin_purge.sh
```

Segredos locais:
- guardar chaves apenas fora de versionamento (`config/secrets/`, `.env`, `*.secrets.toml`).
- qualquer chave exposta em chat/log deve ser revogada e recriada.

---

## 7. Conclusão

Este runbook fecha o fluxo “abrir a pasta e executar o instalador” para Ubuntu Server, mantendo a instalação simples sem comprometer a separação entre runtime autoritativo e memória auxiliar.
