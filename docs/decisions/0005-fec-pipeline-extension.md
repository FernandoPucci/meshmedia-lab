# ADR 0005: Extensao FEC opt-in para o pipeline local

- Status: implementado experimentalmente nas Issues #21 e #22
- Revisao: SDD 0.7.0-draft
- Implementacao de referencia: software 0.1.0, protocolo MM1 1

## Contexto

O contrato FEC da Issue #19 e o Reed-Solomon standalone da Issue #20 geravam
blocos em memoria, mas nao havia uma forma de associar um simbolo recebido ao
bloco, a configuracao e ao comprimento original. O header MM1 v1 e o
Transmission Descriptor v1 nao possuem esses campos.

Alterar o header, o CRC ou o corpo do descritor quebraria os vetores legados e
nao e necessario para o experimento local.

## Decisao

O pipeline usa uma extensao opt-in dentro do payload de pacotes MM1 v1:

- `FLAG_FEC=0x08` seleciona o modo FEC;
- o header de 19 bytes e o CRC-16/CCITT-FALSE permanecem inalterados;
- cada pacote carrega um frame `FC` de versao `1`;
- o frame repete algoritmo, `FecConfig`, comprimento total, bloco, simbolo e
  `FecBlockMetadata`;
- um simbolo e transportado por pacote na primeira implementacao;
- `fragment_number` e `total_fragments` continuam sendo os contadores do
  envelope MM1;
- simbolos de origem sao os indices `0..k-1`; reparos sao `k..n-1`;
- um pacote perdido ou rejeitado pelo CRC corresponde a uma posicao ausente e
  pode ser informado como erasure ao decoder;
- o descritor `TD` v1, quando habilitado, permanece intacto e precede o frame
  somente no primeiro payload.

O frame `FC` tem o layout:

```text
magic(2) | version(1) | algorithm_id_length(1)
| symbol_size(2) | data_symbols(2) | repair_symbols(2)
| block_symbols(2) | interleaving_depth(2)
| padding_policy(1) | incomplete_block_policy(1)
| encoded_length(4) | total_blocks(2) | block_index(2)
| original_length(4) | padding_length(4) | symbol_index(2)
| algorithm_id(N) | symbol_data(symbol_size)
```

O modo sem FEC continua sendo o default. Um RX antigo nao deve ser considerado
compativel com uma transmissao que use `FLAG_FEC`; a extensao exige TX/RX
atualizados.

## Compatibilidade

Esta decisao nao modifica bytes produzidos pelo modo legado nem altera a
semantica de `FIRST_FRAGMENT`, `LAST_FRAGMENT`, `INLINE_DESCRIPTOR` ou CRC.
Ela define uma capacidade experimental adicional para o protocolo v1 local,
nao uma nova versao do protocolo nem uma recomendacao de uso em MeshCore.

## Responsabilidades

- `fec.transmission`: particionar bytes e chamar o `FecEncoder` abstrato;
- `protocol.fec`: serializar frames, criar pacotes MM1 e reagrupar simbolos;
- `Packet`: manter header e CRC;
- `FecDecoder`: recuperar cada bloco;
- `application.pipeline`: coordenar TX, transporte local, RX e codec;
- `apps.local`: expor parametros FEC explicitamente.

Nenhum encoder FEC serializa MM1 ou calcula CRC diretamente.

## Consequencias e limites

- O overhead de um frame por simbolo e deliberadamente alto para o experimento.
- RS continua limitado a `symbol_size=1`, `n <= 255` e sem interleaving.
- ACK/NACK, retransmissao, perdas em rajada e MeshCore permanecem fora desta
  decisao.
- RS(32,28), RS(32,24) e RS(32,20) sao cenarios experimentais, nao presets ou
  parametros de producao.
