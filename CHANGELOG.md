# Changelog

Este arquivo registra mudancas relevantes no software, no protocolo e na
especificacao. Mudancas de documentacao nao alteram automaticamente a versao
do software ou do protocolo.

## [Unreleased]

### Documentacao

- Registrado no SDD o objetivo arquitetural de uma aplicação web local TX/RX, com duas instâncias seriais independentes, estimativa de transmissão e reconstrução visual; criada a Issue #39 para acompanhar sua evolução.
- Atualizada a arquitetura e a ordem de trabalho para manter a aplicação web como objetivo futuro, dependente da validação do transporte MeshCore.

- Adicionada a matriz de rastreabilidade entre SDD e implementacao.
- Adicionada documentacao de CRC, FEC, Reed-Solomon e plano de afericao.
- Adicionada referencia visual e tecnica do formato de pacote MeshCore.
- Adicionada bibliografia com artigos, padroes e fontes de parametrizacao.
- Adicionados registros de decisao para CRC e Reed-Solomon.
- Adicionado o perfil explicito de transmissao em `docs/transmission-profile.md`.
- Adicionada a proposta de Transmission Descriptor inline em
  `docs/transmission-descriptor.md`.
- Adicionada a matriz de experimentos locais e de radio em
  `docs/experiment-matrix.md`.
- Atualizada a arquitetura com as sequencias de pacotes legado e com descritor.
- Registrada como decisão de transporte pendente a comparação entre `GRP_DATA`,
  `TXT_MSG` e `RAW_CUSTOM` para um canal MeshCore privado.
- Registrados na matriz os resultados dos testes manuais TX/RX UDP para imagens
  `64x64` e `32x32`.
- Adicionado o ADR 0003 com a aprovacao do RGB332 e a baseline sem FEC para
  futuras comparacoes com Reed-Solomon.

### Especificacao

- Atualizada a revisao do SDD para `0.4.0-draft`, com quantizacao,
  reconstrução, limites e metricas do experimento RGB332.
- Aprovado o registro RGB332 `0x02` no MM1 v1 sem alterar o cabecalho, usando
  `levels=0` para indicar profundidade fixa `3/3/2`.
- Registradas as execucoes `32x32`/16 mensagens e `64x64`/64 mensagens como
  baseline `fec_algorithm=none` para futuras comparacoes FEC/RS.
- Estabelecida a revisao `0.2.0-draft` do SDD.
- Registrada a matriz experimental RS(32,28), RS(32,24) e RS(32,20).
- Separados os estados implementado, parcial, proposto e planejado.
- Estabelecida a revisao `0.3.0-draft` do SDD.
- Mantido o wire format MM1 v1, com proposta de descritor compacto no primeiro
  payload e sem criacao de protocolo v2.
- Definido o contrato documental abstrato de FEC, sem implementacao de
  Reed-Solomon.
- Registrado o limite inicial proposto de 128 x 128 e a ausencia de presets.

### Implementacao

- Adicionados encoder, decoder, testes e benchmark do experimento RGB332
  isolado; depois da validacao visual, RGB332 foi aprovado como codec da
  implementacao de referencia.
- Adicionados TX/RX UDP locais separados para a validacao visual RGB332, sem
  reutilizar ou alterar o pacote MM1 v1.
- Adicionada a selecao `--codec grayscale|rgb332` aos aplicativos MM1 locais,
  preservando grayscale como default e usando `levels=0` para RGB332.
- Nenhuma mudanca de comportamento no protocolo nesta revisao; FEC e descritor
  continuam sem codigo, enquanto o harness adicional RGB332 permanece
  experimental.
- Aplicado ao grayscale o limite independente de `1..128` pixels para largura e
  altura, com testes para limites, dimensoes nao quadradas e rejeicao de valores
  acima do perfil.
- Mantidos inalterados o cabecalho MM1 v1, seus campos e o CRC-16/CCITT-FALSE.

## [0.1.0] - baseline atual

- Codec grayscale packed.
- Fragmentacao e reassemblagem de pacotes.
- CRC-16/CCITT-FALSE por pacote.
- Simulacao local de perda e corrupcao independente.
- Transporte UDP e aplicacoes locais TX/RX.

Esta versao ainda nao possui uma tag Git de release. O bloco representa a
versao declarada atualmente em `pyproject.toml` e no pacote Python.
