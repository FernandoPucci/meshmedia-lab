# ADR 0003 — Codec RGB332

- **Status:** Aprovado
- **Data:** 2026-11-24
- **Escopo:** codec da implementacao de referencia e transporte local MM1 v1

## Decisao

RGB332 e um codec suportado pelo MeshMedia Lab, selecionavel por
`--codec grayscale|rgb332`. O valor default continua sendo `grayscale` para
preservar o comportamento anterior.

O codec usa um byte por pixel na ordem `RRRGGGBB`, pixels row-major,
quantizacao por piso e reconstrucoes fixas `3/3/2` conforme
`docs/transmission-profile.md`.

## Compatibilidade

O cabecalho MM1 v1 continua com 19 bytes, o CRC continua sendo
CRC-16/CCITT-FALSE e nenhum Transmission Descriptor e necessario. O registro
do codec usa `codec=0x02`. Para esse codec, `levels=0` significa que o campo de
niveis de grayscale nao se aplica; os bits `3/3/2` sao fixos pelo codec.

Um receptor que nao conhece `codec=0x02` deve rejeitar a imagem. Ele nao deve
tentar decodifica-la como grayscale.

## Baseline registrada

Com payload de 64 bytes e sem FEC:

| Codec | Resolucao | Mensagens | Bytes MM1 | Overhead |
|---|---:|---:|---:|---:|
| RGB332 | `32x32` | 16 | 1360 | 336 |
| RGB332 | `64x64` | 64 | 5440 | 1344 |
| Grayscale 16 | `32x32` | 8 | 680 | 168 |
| Grayscale 16 | `64x64` | 32 | 2720 | 672 |

Esses valores sao a baseline `fec_algorithm=none`, `repair_bytes=0` e
`retransmissions=0`. Futuras comparacoes com FEC ou Reed-Solomon devem
preservar imagem, codec, resolucao e payload e registrar reparos e fragmentos
adicionais separadamente.
