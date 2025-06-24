# Odin Zero

Odin Zero é um sistema modular de trading e simulação de estratégias em Python. Esta versão inclui integração com IA local, logging avançado e suporte para extensão futura.

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

### Simulação

```bash
python simulator/run_simulation.py --cenario tendencial
```

Os cenários disponíveis são `tendencial`, `lateral` (padrão) e `volatilidade_alta`.
Os logs e pesos serão guardados respectivamente na pasta `logs/` e no arquivo `pesos.json`.

### Produção

Para iniciar o motor principal:

```bash
python main.py --simular
```

## OpenAI

O módulo `ai/openai/client.py` é um *placeholder*. Para utilizar a API, copie o
arquivo `.env.example` para `.env` e preencha `API_KEY` com a sua chave.

## Mais informações

Consulte o [CHANGELOG](CHANGELOG.md) para detalhes de versão.
