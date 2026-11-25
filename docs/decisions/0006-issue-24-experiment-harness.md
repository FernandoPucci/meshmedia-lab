# ADR 0006: Harness reproduzivel da Issue #24

- Status: implementado experimentalmente
- Revisao: SDD 0.8.0-draft
- Implementacao de referencia: software 0.1.0, protocolo MM1 1

## Contexto

A base do projeto ja possui CRC-16/CCITT-FALSE, Reed-Solomon standalone e
integracao FEC opt-in no pipeline local. Esta decisao define o executor geral
que compara CRC-only, CRC+RS e RS-only com as mesmas imagens, seeds, cenarios e
metricas.

O executor precisa medir o custo real do packetizer FEC atual, inclusive o
caso em que cada simbolo ocupa uma mensagem, sem transformar resultados locais
em afirmacoes sobre radio MeshCore.

## Decisao

O experimento sera implementado como um harness isolado em `benchmarks/issue24`
e produzira artefatos em `experiments/issue-24`. Nenhum campo, tamanho ou
semantica do pacote MM1 v1 sera alterado.

O perfil inicial controlado sera:

- codec grayscale packed;
- `levels=16`;
- payload MM1 de `64` bytes;
- modo `legacy`, sem Transmission Descriptor;
- RS com `symbol_size=1`, sem interleaving;
- `ZERO_PAD` e `PAD_TO_K` nos blocos FEC.

As tres estrategias serao:

1. **CRC-only:** `Fragmenter` e `Reassembler` legados com CRC por pacote;
2. **CRC+RS:** `FecPacketizer` e `FecReassembler` existentes, com CRC por
   pacote e pacotes rejeitados tratados como erasures;
3. **RS-only:** harness local sem `Packet` MM1 e sem CRC, usando
   `FecSymbolFrame` como enquadramento experimental e os mesmos
   `ReedSolomonEncoder`/`ReedSolomonDecoder`.

O caminho RS-only nao e uma variante do MM1 v1 nem uma recomendacao de
transmissao real.

## Falhas e repetibilidade

Um `FaultTrace` deterministico sera indexado pela seed e pela ordem da unidade
transmitida. A mesma seed sera usada para todas as estrategias de uma celula
da matriz. Perda e corrupcao serao registradas separadamente; a corrupcao
alterara bytes do payload ou do simbolo, nunca apenas metadados do simulador.

As taxas solicitadas serao preservadas junto das taxas observadas. Como as
estrategias geram quantidades diferentes de mensagens, o resultado tambem
registrara o numero efetivo de pacotes, simbolos e bytes afetados.

## Contagem de mensagens

Cada fragmento MM1 sera contado como uma mensagem. No RS-only, cada frame
experimental sera contado como uma unidade de mensagem e identificado com
`message_unit=rs_frame`, para nao ser confundido com MM1.

Cada execucao registrara:

- mensagens/unidades enviadas;
- entregues;
- aceitas pelo receptor;
- rejeitadas pelo CRC;
- necessarias para a primeira conclusao valida;
- indice da unidade que permitiu a conclusao.

`messages_sent` continua sendo o custo efetivamente transmitido pelo executor:
o pipeline atual nao interrompe o transmissor quando o receptor ja possui
simbolos suficientes. `messages_used_to_conclude` e uma metrica de suficiência
experimental.

## Overhead

Para CRC-only e CRC+RS, `wire_bytes` inclui payload, header MM1 de 19 bytes e
CRC de 2 bytes por pacote. Para RS-only, `wire_bytes` inclui somente o frame
FEC experimental e o simbolo, sem envelope MM1 e sem CRC. O relatorio deve
manter esses componentes separados e declarar o formato de cada linha.

O percentual será calculado sobre os bytes codificados pelo codec:

```text
overhead (%) = ((wire_bytes - encoded_bytes) / encoded_bytes) * 100
```

Padding, reparos e metadados FEC serão contabilizados separadamente.

## Matriz

A matriz completa utiliza três fixtures, três resoluções, uma estratégia
CRC-only, três configurações CRC+RS, três configurações RS-only, quinze níveis
de cenário e dez repetições: 9.450 execuções.

Execuções parciais são permitidas para desenvolvimento e smoke tests, mas não
substituem nem reduzem silenciosamente a matriz completa.
