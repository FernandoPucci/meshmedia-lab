# Changelog

Este arquivo registra mudancas relevantes no software, no protocolo e na
especificacao. Mudancas de documentacao nao alteram automaticamente a versao
do software ou do protocolo.

## [Unreleased]

### Documentacao

- Adicionada a matriz de rastreabilidade entre SDD e implementacao.
- Adicionada documentacao de CRC, FEC, Reed-Solomon e plano de afericao.
- Adicionada bibliografia com artigos, padroes e fontes de parametrizacao.
- Adicionados registros de decisao para CRC e Reed-Solomon.

### Especificacao

- Estabelecida a revisao `0.2.0-draft` do SDD.
- Registrada a matriz experimental RS(32,28), RS(32,24) e RS(32,20).
- Separados os estados implementado, parcial, proposto e planejado.

### Implementacao

- Nenhuma mudanca de comportamento no software nesta revisao.

## [0.1.0] - baseline atual

- Codec grayscale packed.
- Fragmentacao e reassemblagem de pacotes.
- CRC-16/CCITT-FALSE por pacote.
- Simulacao local de perda e corrupcao independente.
- Transporte UDP e aplicacoes locais TX/RX.

Esta versao ainda nao possui uma tag Git de release. O bloco representa a
versao declarada atualmente em `pyproject.toml` e no pacote Python.
