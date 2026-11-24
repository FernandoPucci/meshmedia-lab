# Status de implementacao

Este documento relaciona a especificacao do laboratorio com o comportamento
efetivamente existente no repositorio. O SDD pode descrever capacidades futuras,
mas esta matriz e a referencia para distinguir proposta, plano e implementacao.

## Linha de base

| Item | Valor |
|---|---|
| Versao do software | `0.1.0` |
| Versao do protocolo binario | `1` |
| Revisao do SDD | `0.4.0-draft` |
| Conformidade | Parcial |
| Ultima revisao | 2026-11-24 |

As versoes do software estao declaradas em `pyproject.toml` e
`src/meshmedia_lab/__init__.py`. A versao do protocolo e declarada por
`PROTOCOL_VERSION` em `src/meshmedia_lab/media.py` e transportada no cabecalho
dos pacotes.

## Status utilizados

| Status | Significado |
|---|---|
| Implementado | Existe codigo, teste automatizado e comportamento documentado. |
| Parcial | Existe codigo, mas ele cobre apenas parte do requisito. |
| Proposto | Existe uma decisao ou desenho tecnico, mas nao existe implementacao. |
| Planejado | Foi identificado como trabalho futuro, sem desenho fechado. |
| Futuro | Visao de longo prazo fora da etapa atual, sem autorizacao de implementacao. |
| Obsoleto | Foi substituido por outra decisao ou abordagem. |

Uma capacidade somente pode ser marcada como implementada quando codigo, testes
e documentacao estiverem coerentes. Uma referencia no SDD, por si so, nao prova
que a capacidade existe.

## Matriz de rastreabilidade

| Capacidade | SDD | Status da especificacao | Status no codigo | Evidencia |
|---|---|---|---|---|
| Codec grayscale packed | Secoes 4, 13 e 24 | Baseline | Implementado | `src/meshmedia_lab/codec/`, `tests/unit/test_codec.py` |
| Fragmentacao de payload | Secoes 6, 7 e 24 | Baseline | Implementado | `src/meshmedia_lab/protocol/fragmenter.py`, testes de protocolo |
| Reassemblagem fora de ordem | Secoes 7 e 24 | Baseline | Implementado | `src/meshmedia_lab/protocol/reassembler.py` |
| Pacote binario atual | Secoes 18 e 19 | Baseline experimental | Implementado | `src/meshmedia_lab/protocol/packet.py` |
| CRC-16/CCITT-FALSE | Secao 8 | Decisao atual | Implementado | `src/meshmedia_lab/protocol/crc.py`, vetor `0x29B1` |
| Transporte UDP local | Secoes 13 e 20 | Baseline de laboratorio | Implementado | `src/meshmedia_lab/transport/udp.py`, testes de integracao |
| Simulacao de perda independente | Secao 11 | Parcial | Implementado | `src/meshmedia_lab/simulation/channel.py` |
| Perda em rajadas, latencia e jitter | Secao 11 | Planejado | Nao implementado | Sem suporte no simulador atual |
| FEC | Secao 9.3 | Proposto | Nao implementado | Sem modulo FEC |
| Reed-Solomon | Secao 10 e Fase 5 | Proposto | Nao implementado | Sem encoder ou decoder RS |
| Parametrizacao RS experimental | Secao 10 e Fase 5 | Proposto | Nao implementado | Matriz documentada, sem experimento executavel |
| Interface abstrata FEC | Etapa A / `docs/error-control.md` | Proposto | Nao implementado | Contrato documental, sem classes ou modulo |
| ACK, NACK e retransmissao | Secao 9.2 e Fase 6 | Planejado | Nao implementado | Sem mensagens de controle |
| Transmissao progressiva | Secao 5 e Fase 8 | Planejado | Nao implementado | Codec atual gera uma representacao unica |
| Integracao MeshCore | Secao 17 e Fase 9 | Planejado | Nao implementado | Sem adaptador; limites em `docs/meshcore-reference.md` |
| Perfil de transmissao parametrizado | Etapa A | Proposto | Nao implementado | `docs/transmission-profile.md`; sem presets no codigo |
| Transmission Descriptor inline | Etapa A | Proposto | Nao implementado | `docs/transmission-descriptor.md`; sem parser ou serializacao |
| Codec RGB332 | Issue #38 / Fase 7 | Aprovado | Implementado | `src/meshmedia_lab/codec/rgb332.py`, testes unitarios, pipeline e aplicativos locais |
| Registro RGB332 no MM1 v1 | Issue #38 / Fase 7 | Aprovado sem alterar layout | Implementado | `media.py` (`codec=0x02`, `levels=0`), `packet.py`, testes UDP locais |
| Limite de 128 x 128 | Ordem de trabalho / Etapa B | Implementado | Implementado | `media.py`, `codec/encoder.py`, `tests/unit/test_codec.py` e `tests/unit/test_protocol.py` |
| Matriz de experimentos | Etapa A | Proposto | Parcial | `docs/experiment-matrix.md`; executor RGB332 isolado em `benchmarks/rgb332_experiment.py` |

## Comportamento atual

O MVP local atualmente funciona desta forma:

1. O TX seleciona grayscale ou RGB332; grayscale permanece o default. RGB332
   usa um byte por pixel e metadata com `codec=0x02` e `levels=0`.
2. O `Fragmenter` divide os bytes em payloads de tamanho configuravel. O
   padrao e 64 bytes e o limite do campo e 255 bytes.
3. Cada `Packet` serializa um cabecalho de 19 bytes, o payload e um CRC de
   2 bytes. O CRC cobre o cabecalho e o payload.
4. O receptor valida o pacote antes de entrega-lo ao reassembler.
5. O reassembler exige todos os fragmentos para concluir a imagem. Nao ha
   recuperacao de fragmentos ausentes.
6. O simulador atual pode descartar um pacote ou alterar um bit de um pacote,
   usando uma semente para permitir repeticao do experimento.
7. Grayscale rejeita largura ou altura fora de `1..128`; RGB332 rejeita valores
   fora de `1..64`. As dimensoes continuam independentes em ambos os codecs.

Consequentemente, uma perda ou uma corrupcao detectada pelo CRC torna a
transmissao incompleta no MVP. FEC e retransmissao sao alternativas futuras,
nao comportamentos disponiveis atualmente.

O modo legado continua sendo o unico caminho implementado. A extensao proposta
de descritor coloca `marker + descriptor_length + descriptor_body` no payload do
primeiro fragmento, mas ainda nao possui marcador final, parser, testes ou
codigo de reassemblagem. Ela nao altera a classificacao do protocolo v1 nem
deve ser tratada como implementada.

## Propostas que ainda nao sao protocolo

O SDD apresenta flags, FEC, ACK/NACK e formatos de cabecalho adicionais como
possibilidades de projeto. Esses elementos nao fazem parte do protocolo binario
versao 1 enquanto nao forem implementados, testados e registrados como uma nova
decisao de compatibilidade.

Em particular, `FEC_PRESENT` aparece no cabecalho conceitual do SDD, mas ainda
nao existe nas flags de `packet.py`. A matriz deve continuar marcando essa
capacidade como proposta.

O descritor inline segue a mesma regra. O cabecalho de 19 bytes, os campos
atuais e o CRC nao podem ser modificados silenciosamente. Enquanto a extensao
nao for revisada e implementada com testes, o primeiro payload continua sendo
somente dados codificados.

## Como atualizar a matriz

Toda mudanca que alterar o comportamento deve atualizar, na mesma revisao:

- o codigo ou teste correspondente;
- a secao do SDD afetada;
- o status nesta matriz;
- a versao do software ou do protocolo, quando aplicavel;
- o `CHANGELOG.md`.

Uma mudanca apenas editorial nao altera a versao do software nem a versao do
protocolo. Ela deve atualizar a revisao do SDD ou o changelog documental.
