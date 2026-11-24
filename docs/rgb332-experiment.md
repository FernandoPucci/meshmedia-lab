# Experimento RGB332

Este documento registra o experimento da Issue #38 e a aprovacao posterior do
RGB332 como codec da implementacao de referencia. O objetivo e comparar a
representacao RGB332 com o codec grayscale packed sem alterar o layout MM1 v1.

## Metodo

- Ambiente: memoria local, UDP localhost experimental e calculo analitico de
  fragmentacao, alem do caminho MM1 local.
- Imagem: `test-images/cat.jpeg`.
- Resolucoes: `32x32` e `64x64`.
- RGB332: um byte por pixel, ordem `RRRGGGBB`.
- Grayscale: codec atual com `16` niveis.
- Payload usado no calculo: `64` bytes.
- Resize: mesma amostragem inteira usada pelo grayscale.
- Envelope: `19` bytes de cabecalho e `2` bytes de CRC por fragmento.
- Descriptor, FEC, ACK/NACK, radio e MeshCore: nao utilizados.
- Baseline de controle de erros: `fec_algorithm=none`, `repair_bytes=0`,
  `retransmissions=0`.

O harness UDP usa datagramas locais com enquadramento proprio para transportar
numero do fragmento, total, dimensoes e payload. Esse enquadramento nao e MM1,
nao usa o cabecalho de 19 bytes e nao altera o protocolo.

Comando executado:

```bash
PYTHONPATH=src:. python3 benchmarks/rgb332_experiment.py \
  --image test-images/cat.jpeg \
  --output-dir artifacts/rgb332 \
  --resolution 32x32 \
  --resolution 64x64
```

O resultado JSON fica em `artifacts/rgb332/results.json`. As imagens geradas
ficam no mesmo diretorio, incluindo uma composicao com referencia RGB, saida
RGB332 e saida grayscale.

## Validacao UDP local

Os processos experimentais podem ser executados em dois terminais:

```bash
PYTHONPATH=src:. python3 -m apps.local.rgb332_rx \
  --bind 127.0.0.1 \
  --port 9001 \
  --output artifacts/rgb332/received-32x32.png \
  --timeout 10 \
  --log-level INFO
```

Em outro terminal:

```bash
PYTHONPATH=src:. python3 -m apps.local.rgb332_tx \
  --image test-images/cat.jpeg \
  --host 127.0.0.1 \
  --port 9001 \
  --resolution 32x32 \
  --payload 64 \
  --image-id 38 \
  --log-level INFO
```

O TX e o RX devem informar `16` mensagens, `1024` bytes de payload RGB332 e
reconstrucao RGB `32x32`. O relatorio deve separar esses valores do custo
hipotetico MM1 de `16` fragmentos e `1360` bytes.

### Execucao observada

Execucao local realizada em `2026-11-24` com `test-images/cat.jpeg`,
`image_id=38`, payload de `64` bytes e porta UDP `9001`:

| Processo | Mensagens | Payload | Bytes de datagrama | Overhead local |
|---|---:|---:|---:|---:|
| TX | 16 | 1024 | 1280 | 256 |
| RX | 16 | 1024 | 1280 | 256 |

O RX concluiu a reconstrução e salvou
`artifacts/rgb332/received-32x32.png`, identificado como PNG RGB `32x32`.
O arquivo recebido foi idêntico ao artefato RGB332 produzido pelo benchmark.
O custo MM1 equivalente, calculado separadamente, permanece em `336` bytes de
overhead e `1360` bytes totais.

Uma segunda execucao foi realizada para `64x64` na porta UDP `9002`:

| Processo | Mensagens | Payload | Bytes de datagrama | Overhead local |
|---|---:|---:|---:|---:|
| TX | 64 | 4096 | 5120 | 1024 |
| RX | 64 | 4096 | 5120 | 1024 |

O RX concluiu a reconstrucao e salvou
`artifacts/rgb332/received-64x64-validation.png`, identificado como PNG RGB
`64x64`. O custo MM1 equivalente e de `1344` bytes de overhead e `5440` bytes
totais.

Esses contadores sao a baseline sem FEC/RS. Futuras execucoes devem preservar
codec, resolucao, imagem e payload e registrar separadamente bytes de reparo,
fragmentos adicionais e sucesso de reconstrucao.

## Validacao MM1 local

Depois da aprovacao do codec, o caminho MM1 existente foi exercitado com a
selecao explicita `--codec rgb332`:

```bash
PYTHONPATH=src:. python3 -m apps.local.rx \
  --bind 127.0.0.1 \
  --port 9003 \
  --output artifacts/rgb332/received-64x64-mm1.png \
  --timeout 10 \
  --log-level INFO
```

Em outro terminal:

```bash
PYTHONPATH=src:. python3 -m apps.local.tx \
  --image test-images/cat.jpeg \
  --host 127.0.0.1 \
  --port 9003 \
  --resolution 64x64 \
  --codec rgb332 \
  --payload 64 \
  --image-id 38 \
  --log-level INFO
```

Resultado observado:

| Processo | Codec | Mensagens | Payload | Bytes MM1 | Overhead | Invalidos |
|---|---|---:|---:|---:|---:|---:|
| TX | RGB332 `32x32` | 16 | 1024 | 1360 | 336 | 0 |
| RX | RGB332 `32x32` | 16 | 1024 | 1360 | 336 | 0 |
| TX | RGB332 | 64 | 4096 | 5440 | 1344 | 0 |
| RX | RGB332 | 64 | 4096 | 5440 | 1344 | 0 |

O arquivo `artifacts/rgb332/received-64x64-mm1.png` foi identificado como PNG
RGB `64x64` e ficou idêntico ao artefato RGB332 do benchmark. Esta execução e a
execucao `32x32` (`artifacts/rgb332/received-32x32-mm1.png`) foram baselines
`fec_algorithm=none` para futuras comparacoes com FEC e Reed-Solomon.

## Resultados locais

| Resolucao | Codec | Bytes | Fragmentos | Overhead MM1 | Total MM1 | PSNR |
|---|---|---:|---:|---:|---:|---:|
| `32x32` | RGB332 | 1024 | 16 | 336 | 1360 | 23.1902 dB |
| `32x32` | Grayscale 16 | 512 | 8 | 168 | 680 | 32.5085 dB |
| `64x64` | RGB332 | 4096 | 64 | 1344 | 5440 | 23.1080 dB |
| `64x64` | Grayscale 16 | 2048 | 32 | 672 | 2720 | 32.4552 dB |

O PSNR RGB332 foi calculado sobre os tres canais RGB. O PSNR grayscale foi
calculado sobre os pixels de luminancia. Os resultados sao especificos da
imagem de entrada e nao representam qualidade geral do codec.

## Artefatos visuais

Os arquivos abaixo foram gerados localmente e estao sob `artifacts/`, que e
ignorado pelo Git:

- `artifacts/rgb332/32x32-comparison.png`
- `artifacts/rgb332/64x64-comparison.png`
- `artifacts/rgb332/32x32-rgb332.png`
- `artifacts/rgb332/64x64-rgb332.png`
- `artifacts/rgb332/32x32-gray16.png`
- `artifacts/rgb332/64x64-gray16.png`
- `artifacts/rgb332/received-32x32-mm1.png`
- `artifacts/rgb332/received-64x64-mm1.png`

A revisao visual humana dos arquivos `32x32` e `64x64` foi aprovada. RGB332
passa a ser codec oficial da implementacao de referencia, enquanto FEC,
Reed-Solomon e outras formas de recuperacao continuam fora desta etapa.

## Limitacoes

- O benchmark nao usa `Packet`, `Fragmenter` ou `Reassembler` para nao atribuir
  semantica grayscale ao campo `levels` do MM1 v1.
- A contagem de fragmentos segue a formula do fragmentador atual.
- Nao houve medicao de UDP, radio, airtime ou MeshCore.
- O ID `0x02` foi registrado para RGB332, com `levels=0` no metadata MM1 v1.
- A integracao posterior no pipeline MM1 local foi registrada no SDD e preservou
  o cabecalho de 19 bytes; o harness UDP independente continua separado.
