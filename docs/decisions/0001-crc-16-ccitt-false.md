# ADR 0001: CRC-16/CCITT-FALSE no protocolo inicial

- Status: aceito para o MVP experimental
- Revisao: SDD 0.2.0-draft
- Implementacao: software 0.1.0, protocolo 1

## Contexto

Cada pacote precisa permitir que o receptor detecte corrupcao no cabecalho ou
no payload antes da reassemblagem. O laboratorio precisa de uma linha de base
simples, portavel e verificavel antes de integrar um radio real.

## Decisao

O protocolo inicial usa CRC-16/CCITT-FALSE por pacote. O CRC e calculado sobre
o cabecalho serializado e o payload, e e anexado como um campo de dois bytes em
ordem de rede.

Os parametros sao `width=16`, `poly=0x1021`, `init=0xFFFF`, `refin=false`,
`refout=false` e `xorout=0x0000`. O vetor `123456789` deve produzir `0x29B1`.

## Justificativa

- O custo fixo de dois bytes e pequeno para o pacote experimental.
- Existe um vetor publico de validacao.
- A verificacao por pacote localiza a corrupcao sem invalidar silenciosamente
  toda a transmissao.
- A implementacao cabe no nucleo sem dependencia externa.

Esta decisao nao afirma que CRC-16 e a melhor escolha final para o airtime real.
O polinomio e o tamanho devem ser reavaliados se os limites do transporte ou o
tamanho dos blocos mudarem.

## Consequencias

O CRC detecta corrupcao, mas nao corrige dados e nao fornece autenticacao. Um
pacote rejeitado pelo CRC fica indisponivel para o reassembler atual. Uma futura
camada FEC podera tratar esse pacote como uma erasure, desde que o indice do
simbolo seja conhecido.

## Evidencia

- `src/meshmedia_lab/protocol/crc.py`
- `src/meshmedia_lab/protocol/packet.py`
- `tests/unit/test_protocol.py`
- [`docs/error-control.md`](../error-control.md)
- [`docs/references.md`](../references.md)
