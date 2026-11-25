# Status de implementacao

Este documento relaciona a especificacao do laboratorio com o comportamento
efetivamente existente no repositorio. O SDD pode descrever capacidades futuras,
mas esta matriz e a referencia para distinguir proposta, plano e implementacao.

## Linha de base

| Item | Valor |
|---|---|
| Versao do software | `0.1.0` |
| Versao do protocolo binario | `1` |
| Revisao do SDD | `0.5.0-draft` |
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
| Transmission Descriptor inline | Issue #17 / ADR 0004 | Contrato v1 definido | Implementado localmente nesta branch; pendente de revisao/integracao | `protocol/descriptor.py`, fragmenter/reassembler, TX/RX, `tests/unit/test_descriptor.py`, `tests/integration/test_descriptor_apps.py` |
| Codec RGB332 | Issue #38 / Fase 7 | Aprovado | Implementado | `src/meshmedia_lab/codec/rgb332.py`, testes unitarios, pipeline e aplicativos locais |
| Registro RGB332 no MM1 v1 | Issue #38 / Fase 7 | Aprovado sem alterar layout | Implementado | `media.py` (`codec=0x02`, `levels=0`), `packet.py`, testes UDP locais |
| Limite grayscale de 128 x 128 | Ordem de trabalho / Etapa B | Implementado | Implementado | `media.py`, `codec/encoder.py`, `tests/unit/test_codec.py` e `tests/unit/test_protocol.py` |
| Limite RGB332 de 64 x 64 | Perfil RGB332 / Etapa B | Implementado | Implementado | `codec/rgb332.py`, `tests/unit/test_rgb332.py` e `tests/integration/test_local_apps.py` |
| Matriz de experimentos | Etapa A | Proposto | Parcial | `docs/experiment-matrix.md`; executor RGB332 isolado em `benchmarks/rgb332_experiment.py` |
| Aplicação web local TX/RX | SDD secao 29 / Issue #39 | Planejado | Nao implementado | Interface localhost e serviço serial ainda não existem |

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

O modo legado continua default. O modo `descriptor` usa flag `0x04` em todos os
pacotes e prefixo `TD | 16 | corpo v1` no fragmento zero. O modelo/parser valida
metadados e comprimento, o reassembler limita dados fora de ordem e rejeita
inconsistencias sem fallback; TX/RX locais e pipeline aceitam os dois modos.
Testes fixam os bytes legados, o CRC e casos positivos/negativos. O corpo atual
nao suporta FEC, compressao ou parametros extras. A entrega nesta branch nao
representa por si so encerramento das Issues #17, #18 ou do agrupador #5.

## Propostas que ainda nao sao protocolo

O SDD apresenta flags, FEC, ACK/NACK e formatos de cabecalho adicionais como
possibilidades de projeto. Esses elementos nao fazem parte do protocolo binario
versao 1 enquanto nao forem implementados, testados e registrados como uma nova
decisao de compatibilidade.

Em particular, `FEC_PRESENT` aparece no cabecalho conceitual do SDD, mas ainda
nao existe nas flags de `packet.py`. A matriz deve continuar marcando essa
capacidade como proposta.

O ADR 0004 registra explicitamente a extensao opcional do descritor, sem mudar
os bytes legados, o cabecalho de 19 bytes ou o CRC. O envio estendido exige RX
atualizado; nao existe negociacao automatica. Futuras alteracoes dessa extensao
continuam sujeitas a especificacao e testes de compatibilidade.

## Verificacao local do descritor (2026-11-24)

Branch `feature/transmission-descriptor`, baseada em `origin/master` `6c9a064`
(PR #42). Esta verificacao local nao significa merge ou fechamento de Issues.

```bash
PYTHONPATH=src:. python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Resultado: 73 testes executados com sucesso, incluindo processos TX/RX UDP
independentes e comparacao de todos os pixels reconstruidos, ambos os codecs,
vetores fixos e permutacoes com seed 17. Os vetores CRC legados tambem foram
conferidos com `binascii.crc_hqx(..., 0xffff)` da biblioteca padrao.
Uma execucao intermediaria detectou erro na formatacao dos novos logs; ele foi
corrigido e a suite completa foi reexecutada.

`git diff --check`: sem problemas. Comandos opcionais tentados:

```bash
python3 -m pytest -q
ruff check .
```

Indisponiveis: `No module named pytest` (exit 1) e `ruff: comando nao encontrado`
(exit 127). Nenhuma dependencia foi adicionada/instalada. Sem ensaio MeshCore,
radio ou FEC; resultados anteriores do benchmark RGB332 nao foram reproduzidos
nem alterados.

## Como atualizar a matriz

Toda mudanca que alterar o comportamento deve atualizar, na mesma revisao:

- o codigo ou teste correspondente;
- a secao do SDD afetada;
- o status nesta matriz;
- a versao do software ou do protocolo, quando aplicavel;
- o `CHANGELOG.md`.

Uma mudanca apenas editorial nao altera a versao do software nem a versao do
protocolo. Ela deve atualizar a revisao do SDD ou o changelog documental.
