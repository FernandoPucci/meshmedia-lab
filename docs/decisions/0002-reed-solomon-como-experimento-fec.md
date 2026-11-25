# ADR 0002: Reed-Solomon como experimento de FEC

- Status: proposto, nao implementado
- Revisao: SDD 0.2.0-draft
- Implementacao de referencia: software 0.1.0, protocolo 1

## Contexto

O transporte desejado pode perder pacotes e pode tornar retransmissoes caras em
airtime. FEC pode recuperar parte das perdas sem exigir um canal de retorno,
mas adiciona bytes, processamento e estado no receptor.

## Decisao provisoria

Reed-Solomon sera avaliado como candidato para FEC em blocos. Os primeiros
experimentos usarao a matriz RS(32,28), RS(32,24) e RS(32,20), com simbolos
explicitamente definidos e, inicialmente, avaliados sobre `GF(2^8)`.

Essas configuracoes nao fazem parte do protocolo versao 1 e nao devem ser
interpretadas como parametros aprovados para producao.

## Justificativa

- Reed-Solomon e adequado para erasures quando a posicao do simbolo ausente e
  conhecida.
- A matriz permite observar o compromisso entre taxa, recuperacao e overhead.
- Os parametros cabem em um experimento pequeno antes da integracao com radio.
- O RFC 5510 oferece terminologia e esquemas de referencia para transporte por
  pacotes.

## O que precisa ser decidido

- Se um simbolo sera um byte, um vetor de payload ou um fragmento inteiro.
- Como o bloco FEC sera identificado no cabecalho.
- Como simbolos de reparo serao identificados e reassemblados.
- Se pacotes invalidos pelo CRC serao tratados como erasures.
- Se sera usada intercalacao para perdas em rajada.
- Qual configuracao minimiza airtime para os padroes de perda observados.

## Criterio para aceitar uma configuracao

Uma configuracao somente podera ser promovida a decisao do protocolo depois de
ser comparada com a baseline sem FEC em perdas aleatorias e em rajadas, usando
as metricas definidas em [`docs/error-control.md`](../error-control.md).

## Consequencias atuais

Existe um modulo de contrato abstrato FEC em
`src/meshmedia_lab/fec/`, mas nao existe campo `FEC_PRESENT`, encoder RS ou
decoder RS no codigo. Qualquer diagrama que mostre Reed-Solomon deve ser
marcado como arquitetura futura ou experimento.
