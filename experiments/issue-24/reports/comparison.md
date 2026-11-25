# Issue #24 — comparação experimental

> Ambiente: simulação local determinística. Estes resultados não são
> medições de MeshCore, LoRa, airtime ou rádio real.

Execuções disponíveis: **9450**.

## Baseline histórico sem FEC

| Resolução | Bytes codificados | Mensagens | Bytes MM1 | Overhead |
|---|---:|---:|---:|---:|
| 32x32 | 512 | 8 | 680 | 168 |
| 64x64 | 2048 | 32 | 2720 | 672 |

Esses valores vêm dos testes manuais documentados em `docs/experiment-matrix.md`. O novo executor deve reproduzi-los para CRC-only sem falhas.

## Observado sem falhas

| Resolução | Estratégia | Mensagens | Necessárias | Wire bytes | Overhead | Sucesso |
|---|---|---:|---:|---:|---:|---:|
| 128x128 | crc+rs-rs32-20-12 | 13120 | 13108.0 | 892160 | 10790.62% | 100.0% |
| 128x128 | crc+rs-rs32-24-8 | 10944 | 10936.0 | 744192 | 8984.38% | 100.0% |
| 128x128 | crc+rs-rs32-28-4 | 9376 | 9372.0 | 637568 | 7682.81% | 100.0% |
| 128x128 | crc-only | 128 | 128.0 | 10880 | 32.81% | 100.0% |
| 128x128 | rs-only-rs32-20-12 | 13120 | 13108.0 | 616640 | 7427.34% | 100.0% |
| 128x128 | rs-only-rs32-24-8 | 10944 | 10936.0 | 514368 | 6178.91% | 100.0% |
| 128x128 | rs-only-rs32-28-4 | 9376 | 9372.0 | 440672 | 5279.30% | 100.0% |
| 32x32 | crc+rs-rs32-20-12 | 832 | 820.0 | 56576 | 10950.00% | 100.0% |
| 32x32 | crc+rs-rs32-24-8 | 704 | 696.0 | 47872 | 9250.00% | 100.0% |
| 32x32 | crc+rs-rs32-28-4 | 608 | 604.0 | 41344 | 7975.00% | 100.0% |
| 32x32 | crc-only | 8 | 8.0 | 680 | 32.81% | 100.0% |
| 32x32 | rs-only-rs32-20-12 | 832 | 820.0 | 39104 | 7537.50% | 100.0% |
| 32x32 | rs-only-rs32-24-8 | 704 | 696.0 | 33088 | 6362.50% | 100.0% |
| 32x32 | rs-only-rs32-28-4 | 608 | 604.0 | 28576 | 5481.25% | 100.0% |
| 64x64 | crc+rs-rs32-20-12 | 3296 | 3284.0 | 224128 | 10843.75% | 100.0% |
| 64x64 | crc+rs-rs32-24-8 | 2752 | 2744.0 | 187136 | 9037.50% | 100.0% |
| 64x64 | crc+rs-rs32-28-4 | 2368 | 2364.0 | 161024 | 7762.50% | 100.0% |
| 64x64 | crc-only | 32 | 32.0 | 2720 | 32.81% | 100.0% |
| 64x64 | rs-only-rs32-20-12 | 3296 | 3284.0 | 154912 | 7464.06% | 100.0% |
| 64x64 | rs-only-rs32-24-8 | 2752 | 2744.0 | 129344 | 6215.62% | 100.0% |
| 64x64 | rs-only-rs32-28-4 | 2368 | 2364.0 | 111296 | 5334.38% | 100.0% |

## Recuperação por cenário

| Resolução | Estratégia | Cenário | Reconstrução integral |
|---|---|---|---:|
| 128x128 | crc+rs-rs32-20-12 | CORRUPT-01 | 100.0% |
| 128x128 | crc+rs-rs32-20-12 | CORRUPT-02 | 100.0% |
| 128x128 | crc+rs-rs32-20-12 | CORRUPT-03 | 100.0% |
| 128x128 | crc+rs-rs32-20-12 | CORRUPT-04 | 16.7% |
| 128x128 | crc+rs-rs32-20-12 | LOSS-01 | 100.0% |
| 128x128 | crc+rs-rs32-20-12 | LOSS-02 | 100.0% |
| 128x128 | crc+rs-rs32-20-12 | LOSS-03 | 100.0% |
| 128x128 | crc+rs-rs32-20-12 | LOSS-04 | 10.0% |
| 128x128 | crc+rs-rs32-20-12 | LOSS-05 | 0.0% |
| 128x128 | crc+rs-rs32-20-12 | MIX-01 | 100.0% |
| 128x128 | crc+rs-rs32-20-12 | MIX-02 | 100.0% |
| 128x128 | crc+rs-rs32-20-12 | MIX-03 | 83.3% |
| 128x128 | crc+rs-rs32-20-12 | MIX-04 | 20.0% |
| 128x128 | crc+rs-rs32-20-12 | MIX-05 | 0.0% |
| 128x128 | crc+rs-rs32-24-8 | CORRUPT-01 | 100.0% |
| 128x128 | crc+rs-rs32-24-8 | CORRUPT-02 | 100.0% |
| 128x128 | crc+rs-rs32-24-8 | CORRUPT-03 | 43.3% |
| 128x128 | crc+rs-rs32-24-8 | CORRUPT-04 | 0.0% |
| 128x128 | crc+rs-rs32-24-8 | LOSS-01 | 100.0% |
| 128x128 | crc+rs-rs32-24-8 | LOSS-02 | 100.0% |
| 128x128 | crc+rs-rs32-24-8 | LOSS-03 | 20.0% |
| 128x128 | crc+rs-rs32-24-8 | LOSS-04 | 0.0% |
| 128x128 | crc+rs-rs32-24-8 | LOSS-05 | 0.0% |
| 128x128 | crc+rs-rs32-24-8 | MIX-01 | 100.0% |
| 128x128 | crc+rs-rs32-24-8 | MIX-02 | 43.3% |
| 128x128 | crc+rs-rs32-24-8 | MIX-03 | 0.0% |
| 128x128 | crc+rs-rs32-24-8 | MIX-04 | 0.0% |
| 128x128 | crc+rs-rs32-24-8 | MIX-05 | 0.0% |
| 128x128 | crc+rs-rs32-28-4 | CORRUPT-01 | 100.0% |
| 128x128 | crc+rs-rs32-28-4 | CORRUPT-02 | 0.0% |
| 128x128 | crc+rs-rs32-28-4 | CORRUPT-03 | 0.0% |
| 128x128 | crc+rs-rs32-28-4 | CORRUPT-04 | 0.0% |
| 128x128 | crc+rs-rs32-28-4 | LOSS-01 | 100.0% |
| 128x128 | crc+rs-rs32-28-4 | LOSS-02 | 0.0% |
| 128x128 | crc+rs-rs32-28-4 | LOSS-03 | 0.0% |
| 128x128 | crc+rs-rs32-28-4 | LOSS-04 | 0.0% |
| 128x128 | crc+rs-rs32-28-4 | LOSS-05 | 0.0% |
| 128x128 | crc+rs-rs32-28-4 | MIX-01 | 83.3% |
| 128x128 | crc+rs-rs32-28-4 | MIX-02 | 0.0% |
| 128x128 | crc+rs-rs32-28-4 | MIX-03 | 0.0% |
| 128x128 | crc+rs-rs32-28-4 | MIX-04 | 0.0% |
| 128x128 | crc+rs-rs32-28-4 | MIX-05 | 0.0% |
| 128x128 | crc-only | CORRUPT-01 | 33.3% |
| 128x128 | crc-only | CORRUPT-02 | 0.0% |
| 128x128 | crc-only | CORRUPT-03 | 0.0% |
| 128x128 | crc-only | CORRUPT-04 | 0.0% |
| 128x128 | crc-only | LOSS-01 | 33.3% |
| 128x128 | crc-only | LOSS-02 | 0.0% |
| 128x128 | crc-only | LOSS-03 | 0.0% |
| 128x128 | crc-only | LOSS-04 | 0.0% |
| 128x128 | crc-only | LOSS-05 | 0.0% |
| 128x128 | crc-only | MIX-01 | 3.3% |
| 128x128 | crc-only | MIX-02 | 0.0% |
| 128x128 | crc-only | MIX-03 | 0.0% |
| 128x128 | crc-only | MIX-04 | 0.0% |
| 128x128 | crc-only | MIX-05 | 0.0% |
| 128x128 | rs-only-rs32-20-12 | CORRUPT-01 | 86.7% |
| 128x128 | rs-only-rs32-20-12 | CORRUPT-02 | 50.0% |
| 128x128 | rs-only-rs32-20-12 | CORRUPT-03 | 0.0% |
| 128x128 | rs-only-rs32-20-12 | CORRUPT-04 | 0.0% |
| 128x128 | rs-only-rs32-20-12 | LOSS-01 | 100.0% |
| 128x128 | rs-only-rs32-20-12 | LOSS-02 | 100.0% |
| 128x128 | rs-only-rs32-20-12 | LOSS-03 | 100.0% |
| 128x128 | rs-only-rs32-20-12 | LOSS-04 | 10.0% |
| 128x128 | rs-only-rs32-20-12 | LOSS-05 | 0.0% |
| 128x128 | rs-only-rs32-20-12 | MIX-01 | 76.7% |
| 128x128 | rs-only-rs32-20-12 | MIX-02 | 3.3% |
| 128x128 | rs-only-rs32-20-12 | MIX-03 | 0.0% |
| 128x128 | rs-only-rs32-20-12 | MIX-04 | 0.0% |
| 128x128 | rs-only-rs32-20-12 | MIX-05 | 0.0% |
| 128x128 | rs-only-rs32-24-8 | CORRUPT-01 | 96.7% |
| 128x128 | rs-only-rs32-24-8 | CORRUPT-02 | 0.0% |
| 128x128 | rs-only-rs32-24-8 | CORRUPT-03 | 0.0% |
| 128x128 | rs-only-rs32-24-8 | CORRUPT-04 | 0.0% |
| 128x128 | rs-only-rs32-24-8 | LOSS-01 | 100.0% |
| 128x128 | rs-only-rs32-24-8 | LOSS-02 | 100.0% |
| 128x128 | rs-only-rs32-24-8 | LOSS-03 | 20.0% |
| 128x128 | rs-only-rs32-24-8 | LOSS-04 | 0.0% |
| 128x128 | rs-only-rs32-24-8 | LOSS-05 | 0.0% |
| 128x128 | rs-only-rs32-24-8 | MIX-01 | 86.7% |
| 128x128 | rs-only-rs32-24-8 | MIX-02 | 0.0% |
| 128x128 | rs-only-rs32-24-8 | MIX-03 | 0.0% |
| 128x128 | rs-only-rs32-24-8 | MIX-04 | 0.0% |
| 128x128 | rs-only-rs32-24-8 | MIX-05 | 0.0% |
| 128x128 | rs-only-rs32-28-4 | CORRUPT-01 | 20.0% |
| 128x128 | rs-only-rs32-28-4 | CORRUPT-02 | 0.0% |
| 128x128 | rs-only-rs32-28-4 | CORRUPT-03 | 0.0% |
| 128x128 | rs-only-rs32-28-4 | CORRUPT-04 | 0.0% |
| 128x128 | rs-only-rs32-28-4 | LOSS-01 | 100.0% |
| 128x128 | rs-only-rs32-28-4 | LOSS-02 | 0.0% |
| 128x128 | rs-only-rs32-28-4 | LOSS-03 | 0.0% |
| 128x128 | rs-only-rs32-28-4 | LOSS-04 | 0.0% |
| 128x128 | rs-only-rs32-28-4 | LOSS-05 | 0.0% |
| 128x128 | rs-only-rs32-28-4 | MIX-01 | 3.3% |
| 128x128 | rs-only-rs32-28-4 | MIX-02 | 0.0% |
| 128x128 | rs-only-rs32-28-4 | MIX-03 | 0.0% |
| 128x128 | rs-only-rs32-28-4 | MIX-04 | 0.0% |
| 128x128 | rs-only-rs32-28-4 | MIX-05 | 0.0% |
| 32x32 | crc+rs-rs32-20-12 | CORRUPT-01 | 100.0% |
| 32x32 | crc+rs-rs32-20-12 | CORRUPT-02 | 100.0% |
| 32x32 | crc+rs-rs32-20-12 | CORRUPT-03 | 100.0% |
| 32x32 | crc+rs-rs32-20-12 | CORRUPT-04 | 83.3% |
| 32x32 | crc+rs-rs32-20-12 | LOSS-01 | 100.0% |
| 32x32 | crc+rs-rs32-20-12 | LOSS-02 | 100.0% |
| 32x32 | crc+rs-rs32-20-12 | LOSS-03 | 100.0% |
| 32x32 | crc+rs-rs32-20-12 | LOSS-04 | 80.0% |
| 32x32 | crc+rs-rs32-20-12 | LOSS-05 | 10.0% |
| 32x32 | crc+rs-rs32-20-12 | MIX-01 | 100.0% |
| 32x32 | crc+rs-rs32-20-12 | MIX-02 | 100.0% |
| 32x32 | crc+rs-rs32-20-12 | MIX-03 | 100.0% |
| 32x32 | crc+rs-rs32-20-12 | MIX-04 | 80.0% |
| 32x32 | crc+rs-rs32-20-12 | MIX-05 | 16.7% |
| 32x32 | crc+rs-rs32-24-8 | CORRUPT-01 | 100.0% |
| 32x32 | crc+rs-rs32-24-8 | CORRUPT-02 | 100.0% |
| 32x32 | crc+rs-rs32-24-8 | CORRUPT-03 | 96.7% |
| 32x32 | crc+rs-rs32-24-8 | CORRUPT-04 | 0.0% |
| 32x32 | crc+rs-rs32-24-8 | LOSS-01 | 100.0% |
| 32x32 | crc+rs-rs32-24-8 | LOSS-02 | 100.0% |
| 32x32 | crc+rs-rs32-24-8 | LOSS-03 | 93.3% |
| 32x32 | crc+rs-rs32-24-8 | LOSS-04 | 6.7% |
| 32x32 | crc+rs-rs32-24-8 | LOSS-05 | 0.0% |
| 32x32 | crc+rs-rs32-24-8 | MIX-01 | 100.0% |
| 32x32 | crc+rs-rs32-24-8 | MIX-02 | 96.7% |
| 32x32 | crc+rs-rs32-24-8 | MIX-03 | 40.0% |
| 32x32 | crc+rs-rs32-24-8 | MIX-04 | 3.3% |
| 32x32 | crc+rs-rs32-24-8 | MIX-05 | 0.0% |
| 32x32 | crc+rs-rs32-28-4 | CORRUPT-01 | 100.0% |
| 32x32 | crc+rs-rs32-28-4 | CORRUPT-02 | 63.3% |
| 32x32 | crc+rs-rs32-28-4 | CORRUPT-03 | 3.3% |
| 32x32 | crc+rs-rs32-28-4 | CORRUPT-04 | 0.0% |
| 32x32 | crc+rs-rs32-28-4 | LOSS-01 | 100.0% |
| 32x32 | crc+rs-rs32-28-4 | LOSS-02 | 73.3% |
| 32x32 | crc+rs-rs32-28-4 | LOSS-03 | 0.0% |
| 32x32 | crc+rs-rs32-28-4 | LOSS-04 | 0.0% |
| 32x32 | crc+rs-rs32-28-4 | LOSS-05 | 0.0% |
| 32x32 | crc+rs-rs32-28-4 | MIX-01 | 100.0% |
| 32x32 | crc+rs-rs32-28-4 | MIX-02 | 6.7% |
| 32x32 | crc+rs-rs32-28-4 | MIX-03 | 0.0% |
| 32x32 | crc+rs-rs32-28-4 | MIX-04 | 0.0% |
| 32x32 | crc+rs-rs32-28-4 | MIX-05 | 0.0% |
| 32x32 | crc-only | CORRUPT-01 | 93.3% |
| 32x32 | crc-only | CORRUPT-02 | 76.7% |
| 32x32 | crc-only | CORRUPT-03 | 63.3% |
| 32x32 | crc-only | CORRUPT-04 | 6.7% |
| 32x32 | crc-only | LOSS-01 | 86.7% |
| 32x32 | crc-only | LOSS-02 | 60.0% |
| 32x32 | crc-only | LOSS-03 | 63.3% |
| 32x32 | crc-only | LOSS-04 | 16.7% |
| 32x32 | crc-only | LOSS-05 | 0.0% |
| 32x32 | crc-only | MIX-01 | 86.7% |
| 32x32 | crc-only | MIX-02 | 36.7% |
| 32x32 | crc-only | MIX-03 | 23.3% |
| 32x32 | crc-only | MIX-04 | 13.3% |
| 32x32 | crc-only | MIX-05 | 0.0% |
| 32x32 | rs-only-rs32-20-12 | CORRUPT-01 | 93.3% |
| 32x32 | rs-only-rs32-20-12 | CORRUPT-02 | 70.0% |
| 32x32 | rs-only-rs32-20-12 | CORRUPT-03 | 13.3% |
| 32x32 | rs-only-rs32-20-12 | CORRUPT-04 | 0.0% |
| 32x32 | rs-only-rs32-20-12 | LOSS-01 | 100.0% |
| 32x32 | rs-only-rs32-20-12 | LOSS-02 | 100.0% |
| 32x32 | rs-only-rs32-20-12 | LOSS-03 | 100.0% |
| 32x32 | rs-only-rs32-20-12 | LOSS-04 | 80.0% |
| 32x32 | rs-only-rs32-20-12 | LOSS-05 | 10.0% |
| 32x32 | rs-only-rs32-20-12 | MIX-01 | 83.3% |
| 32x32 | rs-only-rs32-20-12 | MIX-02 | 50.0% |
| 32x32 | rs-only-rs32-20-12 | MIX-03 | 30.0% |
| 32x32 | rs-only-rs32-20-12 | MIX-04 | 0.0% |
| 32x32 | rs-only-rs32-20-12 | MIX-05 | 0.0% |
| 32x32 | rs-only-rs32-24-8 | CORRUPT-01 | 86.7% |
| 32x32 | rs-only-rs32-24-8 | CORRUPT-02 | 40.0% |
| 32x32 | rs-only-rs32-24-8 | CORRUPT-03 | 0.0% |
| 32x32 | rs-only-rs32-24-8 | CORRUPT-04 | 0.0% |
| 32x32 | rs-only-rs32-24-8 | LOSS-01 | 100.0% |
| 32x32 | rs-only-rs32-24-8 | LOSS-02 | 100.0% |
| 32x32 | rs-only-rs32-24-8 | LOSS-03 | 93.3% |
| 32x32 | rs-only-rs32-24-8 | LOSS-04 | 6.7% |
| 32x32 | rs-only-rs32-24-8 | LOSS-05 | 0.0% |
| 32x32 | rs-only-rs32-24-8 | MIX-01 | 83.3% |
| 32x32 | rs-only-rs32-24-8 | MIX-02 | 10.0% |
| 32x32 | rs-only-rs32-24-8 | MIX-03 | 0.0% |
| 32x32 | rs-only-rs32-24-8 | MIX-04 | 0.0% |
| 32x32 | rs-only-rs32-24-8 | MIX-05 | 0.0% |
| 32x32 | rs-only-rs32-28-4 | CORRUPT-01 | 90.0% |
| 32x32 | rs-only-rs32-28-4 | CORRUPT-02 | 3.3% |
| 32x32 | rs-only-rs32-28-4 | CORRUPT-03 | 0.0% |
| 32x32 | rs-only-rs32-28-4 | CORRUPT-04 | 0.0% |
| 32x32 | rs-only-rs32-28-4 | LOSS-01 | 100.0% |
| 32x32 | rs-only-rs32-28-4 | LOSS-02 | 73.3% |
| 32x32 | rs-only-rs32-28-4 | LOSS-03 | 0.0% |
| 32x32 | rs-only-rs32-28-4 | LOSS-04 | 0.0% |
| 32x32 | rs-only-rs32-28-4 | LOSS-05 | 0.0% |
| 32x32 | rs-only-rs32-28-4 | MIX-01 | 73.3% |
| 32x32 | rs-only-rs32-28-4 | MIX-02 | 0.0% |
| 32x32 | rs-only-rs32-28-4 | MIX-03 | 0.0% |
| 32x32 | rs-only-rs32-28-4 | MIX-04 | 0.0% |
| 32x32 | rs-only-rs32-28-4 | MIX-05 | 0.0% |
| 64x64 | crc+rs-rs32-20-12 | CORRUPT-01 | 100.0% |
| 64x64 | crc+rs-rs32-20-12 | CORRUPT-02 | 100.0% |
| 64x64 | crc+rs-rs32-20-12 | CORRUPT-03 | 100.0% |
| 64x64 | crc+rs-rs32-20-12 | CORRUPT-04 | 53.3% |
| 64x64 | crc+rs-rs32-20-12 | LOSS-01 | 100.0% |
| 64x64 | crc+rs-rs32-20-12 | LOSS-02 | 100.0% |
| 64x64 | crc+rs-rs32-20-12 | LOSS-03 | 100.0% |
| 64x64 | crc+rs-rs32-20-12 | LOSS-04 | 53.3% |
| 64x64 | crc+rs-rs32-20-12 | LOSS-05 | 0.0% |
| 64x64 | crc+rs-rs32-20-12 | MIX-01 | 100.0% |
| 64x64 | crc+rs-rs32-20-12 | MIX-02 | 100.0% |
| 64x64 | crc+rs-rs32-20-12 | MIX-03 | 100.0% |
| 64x64 | crc+rs-rs32-20-12 | MIX-04 | 66.7% |
| 64x64 | crc+rs-rs32-20-12 | MIX-05 | 0.0% |
| 64x64 | crc+rs-rs32-24-8 | CORRUPT-01 | 100.0% |
| 64x64 | crc+rs-rs32-24-8 | CORRUPT-02 | 100.0% |
| 64x64 | crc+rs-rs32-24-8 | CORRUPT-03 | 76.7% |
| 64x64 | crc+rs-rs32-24-8 | CORRUPT-04 | 0.0% |
| 64x64 | crc+rs-rs32-24-8 | LOSS-01 | 100.0% |
| 64x64 | crc+rs-rs32-24-8 | LOSS-02 | 100.0% |
| 64x64 | crc+rs-rs32-24-8 | LOSS-03 | 73.3% |
| 64x64 | crc+rs-rs32-24-8 | LOSS-04 | 0.0% |
| 64x64 | crc+rs-rs32-24-8 | LOSS-05 | 0.0% |
| 64x64 | crc+rs-rs32-24-8 | MIX-01 | 100.0% |
| 64x64 | crc+rs-rs32-24-8 | MIX-02 | 63.3% |
| 64x64 | crc+rs-rs32-24-8 | MIX-03 | 3.3% |
| 64x64 | crc+rs-rs32-24-8 | MIX-04 | 0.0% |
| 64x64 | crc+rs-rs32-24-8 | MIX-05 | 0.0% |
| 64x64 | crc+rs-rs32-28-4 | CORRUPT-01 | 100.0% |
| 64x64 | crc+rs-rs32-28-4 | CORRUPT-02 | 23.3% |
| 64x64 | crc+rs-rs32-28-4 | CORRUPT-03 | 0.0% |
| 64x64 | crc+rs-rs32-28-4 | CORRUPT-04 | 0.0% |
| 64x64 | crc+rs-rs32-28-4 | LOSS-01 | 100.0% |
| 64x64 | crc+rs-rs32-28-4 | LOSS-02 | 16.7% |
| 64x64 | crc+rs-rs32-28-4 | LOSS-03 | 0.0% |
| 64x64 | crc+rs-rs32-28-4 | LOSS-04 | 0.0% |
| 64x64 | crc+rs-rs32-28-4 | LOSS-05 | 0.0% |
| 64x64 | crc+rs-rs32-28-4 | MIX-01 | 96.7% |
| 64x64 | crc+rs-rs32-28-4 | MIX-02 | 0.0% |
| 64x64 | crc+rs-rs32-28-4 | MIX-03 | 0.0% |
| 64x64 | crc+rs-rs32-28-4 | MIX-04 | 0.0% |
| 64x64 | crc+rs-rs32-28-4 | MIX-05 | 0.0% |
| 64x64 | crc-only | CORRUPT-01 | 66.7% |
| 64x64 | crc-only | CORRUPT-02 | 13.3% |
| 64x64 | crc-only | CORRUPT-03 | 0.0% |
| 64x64 | crc-only | CORRUPT-04 | 0.0% |
| 64x64 | crc-only | LOSS-01 | 76.7% |
| 64x64 | crc-only | LOSS-02 | 16.7% |
| 64x64 | crc-only | LOSS-03 | 10.0% |
| 64x64 | crc-only | LOSS-04 | 0.0% |
| 64x64 | crc-only | LOSS-05 | 0.0% |
| 64x64 | crc-only | MIX-01 | 50.0% |
| 64x64 | crc-only | MIX-02 | 6.7% |
| 64x64 | crc-only | MIX-03 | 0.0% |
| 64x64 | crc-only | MIX-04 | 0.0% |
| 64x64 | crc-only | MIX-05 | 0.0% |
| 64x64 | rs-only-rs32-20-12 | CORRUPT-01 | 93.3% |
| 64x64 | rs-only-rs32-20-12 | CORRUPT-02 | 66.7% |
| 64x64 | rs-only-rs32-20-12 | CORRUPT-03 | 3.3% |
| 64x64 | rs-only-rs32-20-12 | CORRUPT-04 | 0.0% |
| 64x64 | rs-only-rs32-20-12 | LOSS-01 | 100.0% |
| 64x64 | rs-only-rs32-20-12 | LOSS-02 | 100.0% |
| 64x64 | rs-only-rs32-20-12 | LOSS-03 | 100.0% |
| 64x64 | rs-only-rs32-20-12 | LOSS-04 | 53.3% |
| 64x64 | rs-only-rs32-20-12 | LOSS-05 | 0.0% |
| 64x64 | rs-only-rs32-20-12 | MIX-01 | 93.3% |
| 64x64 | rs-only-rs32-20-12 | MIX-02 | 30.0% |
| 64x64 | rs-only-rs32-20-12 | MIX-03 | 3.3% |
| 64x64 | rs-only-rs32-20-12 | MIX-04 | 0.0% |
| 64x64 | rs-only-rs32-20-12 | MIX-05 | 0.0% |
| 64x64 | rs-only-rs32-24-8 | CORRUPT-01 | 93.3% |
| 64x64 | rs-only-rs32-24-8 | CORRUPT-02 | 10.0% |
| 64x64 | rs-only-rs32-24-8 | CORRUPT-03 | 0.0% |
| 64x64 | rs-only-rs32-24-8 | CORRUPT-04 | 0.0% |
| 64x64 | rs-only-rs32-24-8 | LOSS-01 | 100.0% |
| 64x64 | rs-only-rs32-24-8 | LOSS-02 | 100.0% |
| 64x64 | rs-only-rs32-24-8 | LOSS-03 | 73.3% |
| 64x64 | rs-only-rs32-24-8 | LOSS-04 | 0.0% |
| 64x64 | rs-only-rs32-24-8 | LOSS-05 | 0.0% |
| 64x64 | rs-only-rs32-24-8 | MIX-01 | 83.3% |
| 64x64 | rs-only-rs32-24-8 | MIX-02 | 0.0% |
| 64x64 | rs-only-rs32-24-8 | MIX-03 | 0.0% |
| 64x64 | rs-only-rs32-24-8 | MIX-04 | 0.0% |
| 64x64 | rs-only-rs32-24-8 | MIX-05 | 0.0% |
| 64x64 | rs-only-rs32-28-4 | CORRUPT-01 | 73.3% |
| 64x64 | rs-only-rs32-28-4 | CORRUPT-02 | 0.0% |
| 64x64 | rs-only-rs32-28-4 | CORRUPT-03 | 0.0% |
| 64x64 | rs-only-rs32-28-4 | CORRUPT-04 | 0.0% |
| 64x64 | rs-only-rs32-28-4 | LOSS-01 | 100.0% |
| 64x64 | rs-only-rs32-28-4 | LOSS-02 | 16.7% |
| 64x64 | rs-only-rs32-28-4 | LOSS-03 | 0.0% |
| 64x64 | rs-only-rs32-28-4 | LOSS-04 | 0.0% |
| 64x64 | rs-only-rs32-28-4 | LOSS-05 | 0.0% |
| 64x64 | rs-only-rs32-28-4 | MIX-01 | 23.3% |
| 64x64 | rs-only-rs32-28-4 | MIX-02 | 0.0% |
| 64x64 | rs-only-rs32-28-4 | MIX-03 | 0.0% |
| 64x64 | rs-only-rs32-28-4 | MIX-04 | 0.0% |
| 64x64 | rs-only-rs32-28-4 | MIX-05 | 0.0% |

## Artefatos

- `results/raw/results.jsonl`: resultados individuais;
- `results/summary/results.csv`: tabela plana;
- `results/summary/summary.json`: agregações;
- `reports/final-analysis.md`: respostas e análise final;
- `reports/charts/`: gráficos SVG;
- `reference/` e `results/images/`: imagens lado a lado.

## Gráficos

- [Overhead](charts/overhead-no-fail.svg)
- [Mensagens](charts/messages-no-fail.svg)
- [Recuperação](charts/recovery-failures.svg)
- [Tempo](charts/time-no-fail.svg)
