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
  --workers 1
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

Viewer local:

```bash
PYTHONPATH=src:. python3 -m benchmarks.issue24.viewer \
  --results-dir experiments/issue-24
```

O viewer usa nearest-neighbor nos dois painéis. Quando `tkinter` não está
disponível, ele inicia automaticamente um viewer HTTP local com a biblioteca
padrão Python. Quando não há reconstrução válida, o painel recebido exibe o
estado da falha e não cria uma imagem preenchida artificialmente.

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
