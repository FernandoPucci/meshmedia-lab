# ADR 0002: Reed-Solomon como experimento de FEC

- Status: implementado como experimento standalone; integracao posterior registrada no ADR 0005
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

## Convencao standalone da Issue #20

Para o primeiro experimento concreto, o campo sera `GF(2^8)` com polinomio
primitivo `0x11D` e elemento gerador `0x02`. Cada simbolo sera um byte e os
pontos de avaliacao serao `alpha^i`, com `i` entre `0` e `n-1`. Os simbolos de
origem ocupam as posicoes `0..k-1`; os simbolos de reparo ocupam
`k..n-1`, gerados por interpolacao sistematica de um polinomio de grau menor
que `k`.

O experimento aceitara `n <= 255`, `symbol_size=1` e
`interleaving_depth=0`. A implementacao sera independente do MM1, do CRC e
dos transportes, usara somente a biblioteca padrao e preservara as politicas
de padding e blocos incompletos do contrato FEC.

## Justificativa

- Reed-Solomon e adequado para erasures quando a posicao do simbolo ausente e
  conhecida.
- A matriz permite observar o compromisso entre taxa, recuperacao e overhead.
- Os parametros cabem em um experimento pequeno antes da integracao com radio.
- O RFC 5510 oferece terminologia e esquemas de referencia para transporte por
  pacotes.

## O que permanece fora desta Issue

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

Existe um modulo de contrato abstrato FEC em `src/meshmedia_lab/fec/`.
A Issue #20 implementa o encoder e o decoder standalone em
`src/meshmedia_lab/fec/reed_solomon.py`, com testes unitarios e sem
dependencias externas. Esta ADR nao definiu a integracao de transporte; a
extensao opt-in posterior esta registrada em
[`0005-fec-pipeline-extension.md`](0005-fec-pipeline-extension.md). Qualquer
resultado de radio continua fora do escopo desta decisao.
