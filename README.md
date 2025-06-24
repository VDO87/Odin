# Odin Zero
![Tests](https://github.com/VDO87/Odin/actions/workflows/python-tests.yml/badge.svg)

Sistema de IA local adaptativa para simulação e otimização de estratégias de trading. Aprende com o histórico de decisões e ajusta pesos dinamicamente. Modular, testável e pronto para integração com APIs externas (como OpenAI ou brokers).

## 🧱 Estrutura do Projeto

```text
Odin/
├── core/           # Núcleo da decisão
├── strategies/     # Estratégias de trading (RSI, MACD, etc.)
├── ai/             # Inteligência artificial local
├── trainer/        # Feedback e ajuste de pesos
├── simulator/      # Gerador de dados de mercado
├── metrics/        # Visualização e métricas
├── tests/          # Testes automatizados
├── main.py         # Ponto de entrada
```

## 🚀 Como Executar

Simulação simples:

```bash
python main.py
```

Com debug:

```bash
python main.py --debug
```

## 🧪 Testes

Para correr todos os testes:

```bash
pytest
```

## 📈 Visualizar pesos

Gera gráfico de pesos atual:

```bash
python metrics/plot_pesos.py
```

## ⚙️ Instalação

Requisitos:

```bash
pip install -r requirements.txt
```

(opcional) Ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

## 🤝 Contribuição

1. Clona o repositório.
2. Cria uma branch com o nome da funcionalidade.
3. Abre um pull request com descrição clara.

## 📝 Licença

Projeto licenciado sob a [Licença MIT](LICENSE).
Veja o [CHANGELOG](CHANGELOG.md) para detalhes das versões.


## 📌 Estado Atual

Versão: v3.0.0
Status: Em desenvolvimento ativo
Objetivo próximo: integração com API externa e refino de feedback inteligente

## 🔭 Roadmap

- v3.1.0 - integração com OpenAI
- v4.0.0 - execução em tempo real

---

Desenvolvido por [VDO87](https://github.com/VDO87)
