# Issue #24 — comparação CRC-only, CRC+RS e RS-only

Este diretório é o destino dos artefatos do experimento local. O executor não
mede MeshCore, LoRa, airtime ou rádio real.

## Execução

Smoke test:

```bash
PYTHONPATH=src:. python3 -m benchmarks.issue24_experiment \
  --output-dir experiments/issue-24 \
  --fixture TEST-01 \
  --resolution 32x32 \
  --scenario NO-FAIL \
  --repetitions 1
```

Matriz completa:

```bash
PYTHONPATH=src:. python3 -m benchmarks.issue24_experiment \
  --output-dir experiments/issue-24 \
  --repetitions 10 \
  --workers 4
```

`--workers N` permite executar células independentes em paralelo. Seeds,
repetições, estratégia, configuração RS e cenário continuam registrados por
execução.

Se uma execução for interrompida, `--resume` pula os JSONs brutos já existentes:

```bash
PYTHONPATH=src:. python3 -m benchmarks.issue24_experiment \
  --output-dir experiments/issue-24 \
  --repetitions 10 \
  --workers 4 \
  --resume
```

Execução direcionada para análise de uma célula:

```bash
PYTHONPATH=src:. python3 -m benchmarks.issue24_experiment \
  --output-dir experiments/issue-24 \
  --fixture TEST-03 \
  --resolution 64x64 \
  --strategy crc+rs \
  --scenario MIX-01 \
  --repetitions 10 \
  --workers 4 \
  --resume
```

`--strategy crc+rs` executa as três configurações RS. Os filtros disponíveis
são `crc-only`, `crc+rs` e `rs-only`.

Viewer local:

```bash
PYTHONPATH=src:. python3 -m benchmarks.issue24.viewer \
  --results-dir experiments/issue-24
```

O viewer usa nearest-neighbor nos dois painéis. Quando `tkinter` não está
disponível, ele inicia automaticamente um viewer HTTP local com a biblioteca
padrão Python. Quando não há reconstrução válida, o painel recebido exibe o
estado da falha e não cria uma imagem preenchida artificialmente.

## Onde acessar os resultados

Após a execução, os principais artefatos são:

```text
experiments/issue-24/reports/final-analysis.md  # análise e recomendação final
experiments/issue-24/reports/comparison.md      # tabelas e links dos gráficos
experiments/issue-24/reports/charts/            # gráficos SVG
experiments/issue-24/results/summary/summary.json
experiments/issue-24/results/summary/results.csv
experiments/issue-24/results/raw/results.jsonl  # todos os resultados
experiments/issue-24/reference/                 # imagens originais
experiments/issue-24/results/images/            # imagens reconstruídas
```

Cada JSON individual possui a mesma identificação no nome do arquivo e registra
seed, repetição, estratégia, configuração RS, cenário, contagem de mensagens,
overhead, recuperação, PSNR e estado da reconstrução.

Para abrir a análise no terminal:

```bash
less experiments/issue-24/reports/final-analysis.md
```

Para comparar uma imagem recebida, procure o JSON com o mesmo prefixo do PNG e
verifique principalmente:

- `reconstruction_integral`;
- `pixels_different`;
- `psnr_db`;
- `messages_sent`;
- `messages_used_to_conclude`;
- `packets_lost`;
- `messages_crc_rejected`;
- `symbols_recovered`.

## Escolha baseada nos resultados

Não existe uma configuração vencedora para todos os objetivos:

| Opção | Resultado observado | Interpretação |
|---|---|---|
| CRC-only | Menor overhead: **32,81%**; recuperação degradada média: **22,30%** | Melhor quando o canal é confiável e o custo de transmissão é prioridade |
| CRC+RS(32,20) | Maior recuperação degradada média: **75,56%**; overhead sem falhas: **10.861,46%** | Melhor escolha experimental quando a prioridade é recuperação |
| RS-only | Recuperação degradada média: **45,24%**; 126 saídas divergentes | Não recomendado para transmissão real; não valida integridade |

**Recomendação:** para o objetivo desta Issue — maximizar a recuperação — a
melhor escolha experimental é **CRC+RS(32,20)**. Para uma transmissão real,
essa escolha ainda não deve ser considerada um preset de produção: o packetizer
atual envia um símbolo FEC por mensagem, gerando overhead muito elevado.

Se a prioridade for reduzir bytes e mensagens, use **CRC-only** como baseline.
O RS-only deve permanecer restrito ao laboratório.

### Recomendação explícita para 64x64 pensando em MeshCore

Para `64x64` com grayscale 16 níveis:

| Opção | Mensagens | Bytes MM1 | Recuperação degradada |
|---|---:|---:|---:|
| CRC-only | 32 | 2.720 | 17,14% |
| CRC+RS(32,20) | 3.296 | 224.128 | 76,67% |

**Escolha recomendada para o packetizer atual:** **CRC-only**, caso o objetivo
seja uma transmissão MeshCore com custo de mensagens controlado. O
`CRC+RS(32,20)` é a melhor opção apenas quando a prioridade absoluta for
recuperação; seu overhead atual é alto demais para ser tratado como uma
configuração de produção.

Antes de usar FEC em MeshCore, deve-se avaliar agregação de símbolos FEC,
fragmentação compatível com o payload real e airtime. O experimento atual usa
payload MM1 de 64 bytes e não inclui o envelope MeshCore real.

## Artefatos

- `config/experiment-matrix.json`: matriz normativa da Issue #24;
- `reference/`: fixtures grayscale determinísticas;
- `results/raw/`: um JSON por execução e `results.jsonl`;
- `results/summary/`: CSV e resumo agregado;
- `results/images/`: imagens recebidas válidas;
- `reports/`: comparação Markdown e gráficos SVG.

As imagens `TEST-01` e `TEST-02` são geradas deterministicamente. `TEST-03`
usa `test-images/cat.jpeg`, existente no repositório, como fixture de detalhes.

Os resultados gerados são locais e devem ser identificados pelo commit,
ambiente e seed registrados nos JSONs.
