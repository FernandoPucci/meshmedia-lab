# Matriz de experimentos do MeshMedia Lab

Este documento define como comparar codecs e controle de erros sem confundir
medicoes do laboratorio local com resultados de radio real.

**Estado:** matriz proposta; o contrato abstrato FEC da Issue #19 e o algoritmo
standalone Reed-Solomon da Issue #20 foram implementados, mas nenhum executor
geral de benchmarks ou integracao FEC/MM1 foi implementado. O executor
específico do experimento RGB332 não substitui esse framework geral.

## 1. Objetivo

A matriz deve comparar, sob as mesmas condicoes:

- somente CRC;
- CRC combinado com Reed-Solomon;
- Reed-Solomon sem CRC, exclusivamente em um experimento controlado.

O objetivo nao e escolher uma configuracao por intuicao. O resultado deve
mostrar o compromisso entre bytes de redundancia, quantidade de mensagens,
recuperacao, custo computacional e sucesso de reconstrução.

Metricas de benchmark pertencem ao laboratorio. Elas nao sao campos do pacote
MM1 e nao devem ser adicionadas ao wire format apenas para facilitar medicao.

## 2. Ambientes

| Ambiente | Descricao | O que pode concluir |
|---|---|---|
| Memoria | `InMemoryTransport` e canal controlado | Comportamento deterministico do pipeline |
| UDP local | TX/RX em `localhost` | Integracao entre processos e datagramas |
| Simulacao | Canal com perda/corrupcao e seed | Sensibilidade a falhas modeladas |
| Radio real | MeshCore/LoRa com firmware identificado | Resultado de transporte e airtime observados |

UDP local nao representa automaticamente perda, jitter, rota mesh, airtime ou
interferencia de radio. Todo resultado deve carregar o ambiente de origem.

## 3. Variaveis controladas

Cada execucao deve registrar todos os valores abaixo.

| Grupo | Valores iniciais |
|---|---|
| Protocolo | MM1 v1, revisao do SDD e commit do codigo |
| Transporte local | memoria ou UDP |
| Codec | grayscale packed; RGB332 aprovado e implementado |
| Dimensoes | `32x32`, `64x32`, `32x64`, `128x128` |
| Niveis grayscale | `2`, `4`, `8`, `16`, `256`, conforme suporte do codec |
| Payload MM1 | `20`, `40`, `60`, `80`, `100` e baseline `64` bytes |
| Limite MeshCore teorico | `144` bytes de payload MM1 para `GRP_DATA`, sem afirmar suporte real |
| Controle de erros | CRC-only, CRC+RS, RS-only controlado |
| Reed-Solomon | RS(32,28), RS(32,24), RS(32,20), quando implementado |
| Perda aleatoria | `0%`, `5%`, `10%`, `20%`, `30%` |
| Corrupcao | Executada separadamente da perda, com taxa registrada |
| Perda em rajada | Cenarios futuros; o simulador atual nao suporta |
| Repeticoes | Numero fixo por celula, com seed registrada |

Dimensoes superiores a 128 x 128, tiling e imagens compostas nao fazem parte
desta matriz inicial.

## 4. Modos de controle de erros

### 4.1 CRC-only

E a baseline implementada no MM1 v1:

```text
dados codificados
  -> fragmentos MM1
  -> CRC-16/CCITT-FALSE por pacote
  -> canal
  -> validacao CRC
  -> reassemblagem se todos os fragmentos existirem
```

Um pacote perdido ou rejeitado pelo CRC nao e recuperado pelo codigo atual.

### 4.2 CRC + Reed-Solomon

E uma configuracao futura de experimento:

```text
dados de origem
  -> blocos e simbolos
  -> Reed-Solomon gera reparos
  -> fragmentos MM1 com CRC
  -> canal
  -> CRC identifica pacotes validos e erasures
  -> decoder FEC tenta recuperar o bloco
  -> reassemblagem dos dados de origem
```

O CRC continua detectando corrupcao. O FEC somente tenta recuperar dados depois
da validacao de cada pacote. A relacao entre fragmento, simbolo e bloco deve
ser registrada na configuracao completa.

### 4.3 RS-only controlado

RS-only nao e um modo adicional do MM1 v1. Ele e um experimento isolado para
medir o algoritmo sem contabilizar o CRC como mecanismo de deteccao.

Regras:

- nao alterar o `Packet` v1;
- nao remover silenciosamente o CRC do protocolo;
- executar em harness de FEC ou em um formato experimental identificado;
- separar perda conhecida de corrupcao desconhecida;
- usar um oraculo de erasure somente quando isso estiver declarado;
- nao comparar RS-only com CRC-only sem registrar que os mecanismos de
  deteccao sao diferentes.

## 5. Matriz minima de cenarios

As celulas abaixo sao o conjunto inicial. Cada celula deve ser repetida para
as dimensoes, codecs e payloads selecionados, sem misturar variaveis durante a
comparacao.

| ID | Controle | Perda | Corrupcao | Ambiente | Estado |
|---|---|---:|---:|---|---|
| C00 | CRC-only | 0% | 0% | memoria/UDP | Executavel com baseline |
| C01 | CRC-only | 5% | 0% | simulacao | Executavel com canal atual |
| C02 | CRC-only | 10% | 0% | simulacao | Executavel com canal atual |
| C03 | CRC-only | 20% | 0% | simulacao | Executavel com canal atual |
| C04 | CRC-only | 30% | 0% | simulacao | Executavel com canal atual |
| C05 | CRC-only | 0% | taxa definida | simulacao | Executavel com canal atual |
| F01 | CRC+RS(32,28) | 5% | 0% | simulacao | Futuro |
| F02 | CRC+RS(32,24) | 10% | 0% | simulacao | Futuro |
| F03 | CRC+RS(32,20) | 20% | 0% | simulacao | Futuro |
| F04 | CRC+RS | rajada | 0% | simulacao | Futuro; canal em rajada ausente |
| R01 | RS-only | 10% | 0% | harness controlado | Futuro |
| R02 | RS-only | 0% | erros conhecidos | harness controlado | Futuro |

As linhas F e R nao representam integracao do protocolo ou funcionalidades de
transporte. Elas documentam experimentos que ainda dependem de um executor
geral, da especificacao dos blocos no wire format e do simulador correspondente;
os testes unitarios da Issue #20 validam somente o algoritmo standalone.

## 6. Variacao de codec e dimensao

Para cada controle de erro, a comparacao deve manter iguais:

- imagem de entrada;
- dimensao alvo;
- codec e seus parametros;
- limite de payload;
- seed e numero de repeticoes;
- versao do software e revisao do protocolo.

O conjunto inicial pode usar:

| Codec | Dimensoes | Parametros |
|---|---|---|
| Grayscale packed | `32x32`, `64x32`, `32x64`, `128x128` | `2`, `16` e `256` niveis |
| RGB332 | `32x32`, `64x64` | `codec=0x02`, canais `3/3/2`, sem compressao |

A matriz deve incluir pelo menos uma imagem nao quadrada para verificar que
largura e altura nao foram confundidas.

## 6.1 Experimento RGB332 da Issue #38

Esta celula registra a validacao inicial do RGB332. O codec foi aprovado para a
implementacao de referencia e o caminho MM1 v1 usa os campos existentes, sem
alterar o layout do cabecalho.

| Campo | Valor do experimento |
|---|---|
| Ambiente | Memoria local, UDP localhost e MM1 local |
| Codec colorido | RGB332 (`codec=0x02`) |
| Dimensoes | `32x32` e `64x64` |
| Limite da API experimental | `1..64` por dimensao |
| Grayscale principal | Packed, `16` niveis |
| Payload para custo | `64` bytes |
| Compressao | Nenhuma |
| Descriptor | Nao utilizado |
| FEC, ACK/NACK | Nao utilizados |
| Transporte | MM1 local ou harness UDP separado |

O grayscale de 16 niveis e o baseline principal por menor custo de transporte,
mantendo-se a possibilidade de repetir o benchmark com outro valor de `levels`.
O executor deve registrar essa escolha e permitir ajuste posterior sem alterar
os bytes do experimento ja registrado.

Para RGB332, a representacao e um byte por pixel na ordem `RRRGGGBB`, com
quantizacao por piso e reconstrucoes fixas conforme o perfil de transmissao.
O custo MM1 e calculado sem descritor:

```text
encoded_bytes = width * height
fragment_count = ceil(encoded_bytes / 64)
header_bytes = fragment_count * 19
crc_bytes = fragment_count * 2
overhead_bytes = header_bytes + crc_bytes
wire_bytes = encoded_bytes + overhead_bytes
```

O objetivo de qualidade e produzir imagens RGB reconstruidas e imagens
grayscale correspondentes para inspeção visual humana no terminal, acompanhadas
de MAE e PSNR. Resultados locais nao devem ser apresentados como medição de
rádio, airtime ou compatibilidade MeshCore.

### 6.2 Baseline para FEC e Reed-Solomon

Os resultados abaixo sao a baseline sem FEC que deve ser preservada para futuras
comparacoes com Reed-Solomon. `repair_bytes=0`, `fec_algorithm=none` e
`retransmissions=0` sao parte do registro da execucao:

| Codec | Resolucao | Encoded bytes | Fragmentos | MM1 overhead | MM1 total | FEC |
|---|---|---:|---:|---:|---:|---|
| RGB332 | `32x32` | 1024 | 16 | 336 | 1360 | none / 0 reparo |
| RGB332 | `64x64` | 4096 | 64 | 1344 | 5440 | none / 0 reparo |
| Grayscale 16 | `32x32` | 512 | 8 | 168 | 680 | none / 0 reparo |
| Grayscale 16 | `64x64` | 2048 | 32 | 672 | 2720 | none / 0 reparo |

Uma futura medicao FEC/RS deve manter a imagem, codec, resolucao e payload
constantes e acrescentar, no minimo, `repair_bytes`, `fec_algorithm`,
`fragment_count`, `packets_sent`, `packets_received` e `reconstruction_success`.

## 7. Variacao de payload

O payload deve ser medido tanto em bytes de dados quanto em quantidade de
mensagens:

```text
fragmentos = ceil(bytes_codificados / payload_limit)
```

No modo com descritor inline:

```text
primeiro_payload_util = payload_limit - descritor_bytes
```

O tamanho do descritor deve aparecer separadamente. Nao se deve atribuir ao
codec um aumento causado apenas pelo prefixo de configuracao.

## 8. Metricas obrigatorias

### Dados e overhead

| Metrica | Definicao |
|---|---|
| `source_bytes` | Representacao de entrada medida pelo experimento |
| `encoded_bytes` | Bytes produzidos pelo codec antes de fragmentar |
| `descriptor_bytes` | Bytes consumidos pelo descritor inline |
| `repair_bytes` | Bytes de reparo FEC |
| `payload_bytes` | Soma dos payloads MM1 |
| `header_bytes` | Soma dos cabecalhos MM1 |
| `crc_bytes` | Dois bytes por pacote MM1 |
| `wire_bytes` | Cabecalho + payload + CRC de todos os pacotes |
| `fragment_count` | Quantidade de pacotes MM1 produzidos |

### Canal e recuperacao

| Metrica | Definicao |
|---|---|
| `packets_sent` | Pacotes entregues ao canal |
| `packets_received` | Pacotes recebidos antes da validacao |
| `packets_lost` | Pacotes removidos pelo canal |
| `crc_rejected` | Pacotes descartados por CRC |
| `duplicates` | Pacotes ou simbolos repetidos |
| `out_of_order` | Pacotes recebidos fora da ordem |
| `symbols_recovered` | Simbolos reconstruidos pelo FEC |
| `reconstruction_success` | Imagem reconstruida integralmente |
| `failure_reason` | Motivo padronizado da falha |

### Custo e qualidade

| Metrica | Definicao |
|---|---|
| `encode_time` | Tempo de codificacao |
| `decode_time` | Tempo de decodificacao |
| `fec_encode_time` | Tempo de geracao de reparos |
| `fec_decode_time` | Tempo de recuperacao |
| `reassembly_time` | Tempo de reassemblagem |
| `memory_peak` | Memoria maxima observada, quando medida |
| `latency` | Tempo total no ambiente avaliado |
| `airtime_estimated` | Estimativa baseada em parametros declarados |
| `airtime_measured` | Medicao feita em radio real |
| `PSNR` / `SSIM` | Qualidade visual quando aplicavel |

PSNR e SSIM nao substituem `reconstruction_success`. Uma imagem pode ser
reconstruida com sucesso no formato, mas ter qualidade diferente por causa do
codec.

## 9. Registro de uma execucao

Cada resultado deve guardar, no minimo:

```text
environment=memory|udp-local|radio-real
software_version=...
protocol_version=1
sdd_revision=...
repository_commit=...
image_fixture=...
width=...
height=...
codec_id=...
codec_parameters=...
payload_limit=...
descriptor_mode=legacy|inline
fec_algorithm=none|...
fec_parameters=...
loss_model=...
corruption_model=...
seed=...
repetitions=...
```

Resultados de simulacao devem ser rotulados como simulacao. Eles nao devem ser
apresentados como taxa de perda, airtime ou alcance de radio real.

## 10. Criterios de comparacao

Uma configuracao so pode ser considerada melhor em um criterio quando:

- usa a mesma imagem e parametros de codec;
- usa o mesmo limite de payload;
- usa o mesmo modelo de canal e sementes equivalentes;
- registra o mesmo numero de repeticoes;
- separa bytes de origem, reparo, cabecalho e CRC;
- informa se a reconstrucao foi integral;
- identifica claramente o ambiente de execucao.

Nao existe uma configuracao vencedora definida nesta etapa. A escolha futura
deve considerar sucesso de reconstrucao, overhead, airtime e processamento em
conjunto.

## 11. Lacunas do simulador atual

O `ChannelSimulator` atual suporta perda independente, corrupcao de um bit,
limite de payload e seed reproduzivel. Ainda nao suporta:

- perda em rajadas;
- latencia;
- jitter;
- duplicacao automatica;
- interrupcao;
- modelo de radio ou airtime.

Esses cenarios permanecem planejados e nao devem ser marcados como resultados
executados.

## 12. Resultados locais registrados

Os resultados abaixo sao de testes manuais TX/RX executados em `2026-11-24`.
Eles foram realizados em UDP sobre `localhost`, com `DISPLAY=:1` e `--display`
habilitado no RX. Nao sao medições de MeshCore, LoRa ou radio real.

| Campo | Valor comum |
|---|---|
| Commit | `0b88475` |
| Protocolo | MM1 v1 |
| Transporte | UDP local |
| Codec | Grayscale packed (`0x01`) |
| Niveis | 16 |
| Limite de payload MM1 | 64 bytes |
| Overhead por pacote | 21 bytes: 19 de cabecalho + 2 de CRC |
| Corrupcao/perda | 0% no teste |
| Resultado | Reconstrucao completa; `invalid_packets=0` |

| Imagem | Dados codificados | Mensagens TX/RX | Payload total | Bytes MM1 totais | Overhead total | Saida RX |
|---|---:|---:|---:|---:|---:|---|
| `test-images/64x64.jpeg` | 2048 bytes | 32 | 2048 bytes | 2720 bytes | 672 bytes | PNG grayscale `64x64` |
| `test-images/32x32.jpeg` | 512 bytes | 8 | 512 bytes | 680 bytes | 168 bytes | PNG grayscale `32x32` |

Os valores seguem o empacotamento atual de 4 bits por pixel:

```text
64 x 64 x 4 / 8 = 2048 bytes
ceil(2048 / 64) = 32 mensagens

32 x 32 x 4 / 8 = 512 bytes
ceil(512 / 64) = 8 mensagens
```

Os logs completos foram gerados durante a execucao em arquivos temporarios
locais. O resumo observado no TX e no RX foi:

```text
64x64: messages=32, payload_bytes=2048, message_bytes_total=2720,
       overhead_bytes=672, invalid_packets=0
32x32: messages=8, payload_bytes=512, message_bytes_total=680,
       overhead_bytes=168, invalid_packets=0
```

Esses ensaios sao smoke tests manuais, nao um executor de benchmark. O resultado
nao inclui o envelope externo MeshCore nem decide entre `GRP_DATA`, `TXT_MSG` e
`RAW_CUSTOM`.
