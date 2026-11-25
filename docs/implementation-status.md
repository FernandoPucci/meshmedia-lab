# Status de implementacao

Este documento relaciona a especificacao do laboratorio com o comportamento
efetivamente existente no repositorio. O SDD pode descrever capacidades futuras,
mas esta matriz e a referencia para distinguir proposta, plano e implementacao.

## Linha de base

| Item | Valor |
|---|---|
| Versao do software | `0.1.0` |
| Versao do protocolo binario | `1` |
| Revisao do SDD | `0.8.0-draft` |
| Conformidade | Parcial |
| Ultima revisao | 2026-11-25 |

As versoes do software estao declaradas em `pyproject.toml` e
`src/meshmedia_lab/__init__.py`. A versao do protocolo e declarada por
`PROTOCOL_VERSION` em `src/meshmedia_lab/media.py` e transportada no cabecalho
dos pacotes.

## Status utilizados

| Status | Significado |
|---|---|
| Implementado | Existe codigo, teste automatizado e comportamento documentado. |
| Parcial | Existe codigo, mas ele cobre apenas parte do requisito. |
| Experimento standalone | Existe codigo e teste isolado, sem integracao de protocolo ou transporte. |
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
| FEC standalone | Secao 9.3 | Experimento standalone | Implementado | Reed-Solomon funcional; `src/meshmedia_lab/fec/reed_solomon.py` |
| Reed-Solomon | Secao 10 e Fase 5 | Experimento standalone | Implementado | `ReedSolomonEncoder`, `ReedSolomonDecoder` e `tests/unit/test_reed_solomon.py` |
| Parametrizacao RS experimental | Secao 10 e Fase 5 | Experimento standalone | Parcial | RS(32,28), RS(32,24), RS(32,20) e vetores unitarios; sem executor geral |
| Interface abstrata FEC | Issue #19 / `docs/error-control.md` | Contrato implementado | Implementado | `src/meshmedia_lab/fec/contract.py`, `tests/unit/test_fec.py` |
| Preparacao de blocos FEC no TX | Issues #21/#22 | Integracao local opt-in | Implementado | `src/meshmedia_lab/fec/transmission.py`, `tests/unit/test_fec_transmission.py` |
| Frames FEC no MM1 | Issues #21/#22 | Extensao experimental opt-in | Implementado | `FLAG_FEC=0x08`, `protocol/fec.py`, `tests/unit/test_fec_protocol.py` |
| Recuperacao FEC no RX | Issue #22 | Integracao local opt-in | Implementado | `FecReassembler`, pipeline e testes UDP |
| ACK, NACK e retransmissao | Secao 9.2 e Fase 6 | Planejado | Nao implementado | Sem mensagens de controle |
| Transmissao progressiva | Secao 5 e Fase 8 | Planejado | Nao implementado | Codec atual gera uma representacao unica |
| Integracao MeshCore | Secao 17 e Fase 9 | Planejado | Nao implementado | Sem adaptador; limites em `docs/meshcore-reference.md` |
| Perfil de transmissao parametrizado | Etapa A | Proposto | Nao implementado | `docs/transmission-profile.md`; sem presets no codigo |
| Transmission Descriptor inline | Issue #17 / ADR 0004 | Contrato v1 definido | Implementado e integrado ao master pela PR #43 | `protocol/descriptor.py`, fragmenter/reassembler, TX/RX, `tests/unit/test_descriptor.py`, `tests/integration/test_descriptor_apps.py` |
| Codec RGB332 | Issue #38 / Fase 7 | Aprovado | Implementado | `src/meshmedia_lab/codec/rgb332.py`, testes unitarios, pipeline e aplicativos locais |
| Registro RGB332 no MM1 v1 | Issue #38 / Fase 7 | Aprovado sem alterar layout | Implementado | `media.py` (`codec=0x02`, `levels=0`), `packet.py`, testes UDP locais |
| Limite grayscale de 128 x 128 | Ordem de trabalho / Etapa B | Implementado | Implementado | `media.py`, `codec/encoder.py`, `tests/unit/test_codec.py` e `tests/unit/test_protocol.py` |
| Limite RGB332 de 64 x 64 | Perfil RGB332 / Etapa B | Implementado | Implementado | `codec/rgb332.py`, `tests/unit/test_rgb332.py` e `tests/integration/test_local_apps.py` |
| Matriz de experimentos | Etapa A / Issue #24 | Executado localmente | Implementado | `experiments/issue-24/reports/final-analysis.md`, 9.450 resultados |
| Fixtures deterministicas da Issue #24 | Issue #24 | Especificado | Implementado | `benchmarks/issue24/fixtures.py`, testes de seed/paleta e manifest |
| Executor geral CRC/FEC | Issue #24 / Etapa D | Executado localmente | Implementado experimentalmente | `benchmarks/issue24/`, 9.450 resultados brutos e resumo |
| Harness RS-only | Issue #24 | Isolado, sem MM1 v1 | Implementado | `benchmarks/issue24/strategies.py`, sem `Packet` ou CRC |
| Metricas de mensagens e conclusao | Issue #24 | Especificado | Implementado | `benchmarks/issue24/runner.py`, JSON/CSV e testes |
| Comparacao visual Issue #24 | Issue #24 | Especificado | Implementado | `benchmarks/issue24/viewer.py`, viewer local com nearest-neighbor |
| WebApp browser-only TX/RX | SDD seção 29 / Issue #39 | Planejado | Não implementado | GitHub Pages + Web Bluetooth; execução do codec Python existente no browser (PoC Pyodide pendente); sem backend local |

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
transmissao incompleta no caminho legado. Quando `FLAG_FEC=0x08` e usado, o
`FecReassembler` agrupa os frames por bloco e simbolo, infere erasures
ausentes, chama o decoder FEC e somente entrega os bytes ao codec quando todos
os blocos foram recuperados. O modo FEC continua experimental e opt-in; nao ha
ACK/NACK nem retransmissao.

O modo legado continua default. O modo `descriptor` usa flag `0x04` em todos os
pacotes e prefixo `TD | 16 | corpo v1` no fragmento zero. O modelo/parser valida
metadados e comprimento, o reassembler limita dados fora de ordem e rejeita
inconsistencias sem fallback; TX/RX locais e pipeline aceitam os dois modos.
O modo FEC usa adicionalmente `FLAG_FEC=0x08` e frames `FC` repetidos por
simbolo; o corpo do descritor permanece sem campos FEC. Testes fixam os bytes
legados, o CRC, o descritor e a extensao FEC. A PR #43 integrou o descritor ao
master; as Issues #17, #18 e #5 foram encerradas apos a revisao das evidencias
do merge.

## Propostas que ainda nao sao protocolo

O SDD ainda apresenta ACK/NACK e formatos adicionais como possibilidades de
projeto. Eles nao fazem parte do protocolo binario versao 1. A extensao FEC
experimental agora implementada e uma capacidade opt-in que exige TX/RX
atualizados; ela nao altera o caminho legado nem deve ser tratada como
interoperabilidade transparente.

`FLAG_FEC=0x08` e reservado para a extensao experimental atual. A flag
`INLINE_DESCRIPTOR=0x04` continua exclusiva do Transmission Descriptor e nao
foi reutilizada.

O ADR 0004 registra explicitamente a extensao opcional do descritor, sem mudar
os bytes legados, o cabecalho de 19 bytes ou o CRC. O envio estendido exige RX
atualizado; nao existe negociacao automatica. Futuras alteracoes dessa extensao
continuam sujeitas a especificacao e testes de compatibilidade.

## Verificacao da PR #43 (2026-11-24)

A implementacao do descritor foi integrada ao `master` pela PR #43, merge commit
`6173befa6daf67625e21e0eed3c866b2c424253d`, a partir da branch
`feature/transmission-descriptor` (`a7f05f2`). A PR registra a execucao local da
suite e os resultados abaixo. As Issues #17, #18 e #5 foram encerradas apos
revisao das evidencias e do estado integrado.

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

## Verificacao da Issue #20 (2026-11-25)

A implementacao standalone foi validada sem alterar o protocolo MM1 v1, o
cabecalho, o descritor ou o CRC. Os testes cobrem vetores independentes,
codificacao dos tres tamanhos experimentais, padding, erasures, erros
desconhecidos, combinacoes no limite `2e + s <= n-k`, falhas acima do limite,
indices duplicados e compatibilidade com os protocolos FEC.

```bash
PYTHONPATH=src:. python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m pytest -q
ruff check src/meshmedia_lab/fec tests/unit/test_reed_solomon.py
```

Resultado registrado: 104 testes passaram no `unittest`, 104 testes passaram
no `pytest` e a verificacao Ruff da camada FEC passou. Nao foi adicionada
dependencia externa. A execucao global do Ruff ainda possui apontamentos
preexistentes fora da camada desta Issue.

## Verificacao das Issues #21 e #22 (2026-11-25)

A preparacao FEC, os frames opt-in, a recuperacao no RX e os caminhos locais
foram implementados sem alterar os vetores legados do MM1 v1. A extensao usa
`FLAG_FEC=0x08` e frames `FC`; o header, o CRC e o descritor v1 permanecem
inalterados.

```bash
PYTHONPATH=src:. python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m pytest -q
ruff check src/meshmedia_lab/fec \
  src/meshmedia_lab/protocol/fec.py \
  src/meshmedia_lab/protocol/__init__.py \
  src/meshmedia_lab/application/pipeline.py \
  apps/local/tx.py apps/local/rx.py \
  tests/unit/test_fec_transmission.py tests/unit/test_fec_protocol.py \
  tests/integration/test_pipeline.py tests/integration/test_local_apps.py
git diff --check
```

Resultado: 122 testes passaram; a verificacao Ruff dos arquivos da entrega
passou; `git diff --check` nao encontrou problemas. Os testes cobrem
grayscale, RGB332, blocos multiplos, padding, perdas, rejeicoes por CRC,
falha por simbolos insuficientes, modo descriptor e TX/RX UDP local.
`python3 -m pytest -q` tambem passou com 122 testes e 336 subtests, com um
warning de deprecacao originado pelo plugin `anyio`.

As configuracoes RS(32,28), RS(32,24) e RS(32,20) foram exercitadas no
pipeline sem declarar nenhuma como recomendada para producao. Nenhum teste de
MeshCore ou radio real foi executado. A verificacao global do Ruff ainda possui
29 apontamentos preexistentes fora dos arquivos desta entrega.

## Como atualizar a matriz

Toda mudanca que alterar o comportamento deve atualizar, na mesma revisao:

- o codigo ou teste correspondente;
- a secao do SDD afetada;
- o status nesta matriz;
- a versao do software ou do protocolo, quando aplicavel;
- o `CHANGELOG.md`.

Uma mudanca apenas editorial nao altera a versao do software nem a versao do
protocolo. Ela deve atualizar a revisao do SDD ou o changelog documental.


## Diretriz arquitetural da WebApp (2026-11-25)

A WebApp será estática e browser-only, hospedada em GitHub Pages/HTTPS. Não
haverá backend, servidor localhost, instalação ou processo auxiliar na máquina
do usuário. O Companion Bluetooth atual permanece como caminho primário via
Web Bluetooth.

**O codec Python já existente é reutilizado sem qualquer modificação.** A
hipótese para executá-lo no navegador é Pyodide/WebAssembly, ainda pendente de
prova de conceito. Nenhum arquivo, API, algoritmo, vetor binário ou teste do
codec pode ser alterado para atender à WebApp. Se a execução browser-only não
for viável sem modificar o codec, a implementação deve parar para decisão
humana. Adaptadores e wrappers novos ficam fora da camada de codec.

A biblioteca meshcore.js é candidata para conexão BLE e operações do
Companion; API, licença e suporte ao envio/recepção binária de grupo ainda
precisam ser validados. Chrome/Edge desktop são o alvo inicial; Linux deve ser
testado cedo. Não há integração MeshCore real comprovada nesta revisão.
