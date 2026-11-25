# Changelog

Este arquivo registra mudancas relevantes no software, no protocolo e na
especificacao. Mudancas de documentacao nao alteram automaticamente a versao
do software ou do protocolo.

## [Unreleased]

### Correcao documental apos PR #43

- Atualizado `docs/implementation-status.md` para refletir que o Transmission Descriptor inline esta implementado e integrado ao `master` pela PR #43.
- Atualizada a verificacao da implementacao para identificar a PR mergeada, seu merge commit e os resultados de teste registrados na propria PR.
- Atualizado o estado do ADR 0004 para implementado/integrado, sem alterar o contrato tecnico aprovado.
- Issues #17, #18 e #5 foram encerradas apos revisao das evidencias da PR #43.

### Documentacao

- Documentado o contrato inline v1 e a decisao de compatibilidade no ADR 0004,
  substituindo de forma rastreavel a proposta preliminar da Etapa A.
- Alinhado o perfil de transmissão, a matriz de implementação e o experimento
  RGB332 para distinguir claramente os limites grayscale `128x128` e RGB332
  `64x64`, além do estado do registro `codec=0x02`.
- Esclarecido que o executor RGB332 específico não representa um framework geral
  de benchmarks.
- Registrado o contrato experimental isolado do RGB332 da Issue #38, sem alteracao do envelope MM1 v1.

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

- SDD `0.5.0-draft`: extensao opt-in INLINE_DESCRIPTOR (`0x04`), marcador `TD`,
  corpo fixo big-endian de 16 bytes, encoded_length uint32 obrigatorio e
  comparacao dos metadados duplicados com o header. Nenhuma mudanca nos bytes
  legados, offsets do header MM1 v1 ou CRC-16/CCITT-FALSE.
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

- Implementado o contrato abstrato de FEC da Issue #19 em
  `src/meshmedia_lab/fec/`, com configuracao imutavel, simbolos, blocos,
  resultados, protocolos separados e validacoes cobertas por fake; nenhum
  algoritmo FEC ou integracao MM1 foi adicionada.
- Implementados modelo/parser puro do descritor, fragmentacao opt-in,
  reassemblagem fora de ordem limitada, validacao estrita e rejeicao terminal
  de descritores inconsistentes, com integracao aos dois codecs, pipeline e
  TX/RX locais (`--transmission-mode legacy|descriptor`; legado default).
- Adicionados vetores fixos, falhas de parsing/metadata/comprimento, duplicatas,
  limites de payload, CRC e ensaios TX/RX UDP sem produzir imagem em falhas.
- Ampliada a cobertura automatizada para dimensões zero e negativas, entradas
  inválidas grayscale, limites RGB332, dimensões independentes e transmissão
  MM1 RGB332 em `64x64`.
- Adicionados encoder, decoder, testes e benchmark do experimento RGB332
  isolado; depois da validacao visual, RGB332 foi aprovado como codec da
  implementacao de referencia.
- Adicionados TX/RX UDP locais separados para a validacao visual RGB332, sem
  reutilizar ou alterar o pacote MM1 v1.
- Adicionada a selecao `--codec grayscale|rgb332` aos aplicativos MM1 locais,
  preservando grayscale como default e usando `levels=0` para RGB332.
- Na revisao historica do experimento RGB332, FEC e descritor ainda nao tinham
  codigo; o harness adicional RGB332 permanece experimental. A implementacao
  posterior do descritor esta registrada acima; FEC continua sem codigo.
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
