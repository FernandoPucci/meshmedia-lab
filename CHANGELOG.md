# Changelog

Este arquivo registra mudancas relevantes no software, no protocolo e na
especificacao. Mudancas de documentacao nao alteram automaticamente a versao
do software ou do protocolo.

## [Unreleased]

### Documentacao

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

### Especificacao

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

- Nenhuma mudanca de comportamento no software nesta revisao; RGB332, FEC,
  descritor e benchmarks continuam sem codigo.

## [0.1.0] - baseline atual

- Codec grayscale packed.
- Fragmentacao e reassemblagem de pacotes.
- CRC-16/CCITT-FALSE por pacote.
- Simulacao local de perda e corrupcao independente.
- Transporte UDP e aplicacoes locais TX/RX.

Esta versao ainda nao possui uma tag Git de release. O bloco representa a
versao declarada atualmente em `pyproject.toml` e no pacote Python.
