# Controle de erros e recuperacao

Este documento explica as tecnicas de integridade e recuperacao consideradas
para o MeshMedia Lab e separa explicitamente o que ja existe do que ainda e
proposta experimental.

| Item | Estado atual |
|---|---|
| CRC-16/CCITT-FALSE | Implementado por pacote |
| Contrato abstrato FEC | Implementado |
| FEC standalone | Reed-Solomon implementado para experimentos isolados |
| Preparacao FEC no TX | Implementada sobre o contrato abstrato |
| Integracao FEC opt-in no MM1 | Implementada como extensao experimental |
| Recuperacao FEC no RX | Implementada no pipeline local |
| Retransmissao seletiva | Nao implementada |

O estado completo de conformidade esta em
[`implementation-status.md`](implementation-status.md).

Os parametros de transmissao e o descritor inline atual (sem campos FEC)
estao em [`transmission-profile.md`](transmission-profile.md) e
[`transmission-descriptor.md`](transmission-descriptor.md). Os cenarios de
comparacao estao em [`experiment-matrix.md`](experiment-matrix.md).

## 1. Quatro conceitos diferentes

| Conceito | Pergunta respondida | Papel no projeto |
|---|---|---|
| CRC-16 | Os bytes recebidos provavelmente estao inteiros? | Detectar corrupcao |
| CCITT-FALSE | Qual parametrizacao do CRC-16 esta sendo usada? | Definir o algoritmo sem ambiguidade |
| FEC | Como adicionar redundancia para recuperar dados sem retorno? | Categoria de tecnicas |
| Reed-Solomon | Qual codigo pode gerar simbolos de reparo? | Candidato de FEC |

CRC detecta. Reed-Solomon pode recuperar. FEC e o conjunto de estrategias que
usa redundancia para corrigir ou recuperar. Os termos nao sao sinonimos.

## 2. Caminho implementado atualmente

```text
Imagem
  -> encoder grayscale ou RGB332
  -> [sem FEC] descritor opcional -> fragmentacao MM1 v1
  -> [com FEC] blocos -> simbolos de origem/reparo -> frames FEC
  -> cabecalho MM1 v1 + payload + CRC-16/CCITT-FALSE
  -> transporte local UDP ou em memoria
  -> validacao do CRC
  -> [sem FEC] reassemblagem legada
  -> [com FEC] agrupamento por bloco/simbolo -> decoder FEC
  -> decoder de imagem
```

No caminho sem FEC, um pacote perdido ou rejeitado pelo CRC continua tornando
a transmissao incompleta. No caminho FEC, a posicao ausente e informada como
erasure ao decoder quando ainda houver simbolos suficientes no bloco.

## 3. CRC-16/CCITT-FALSE

CRC significa *Cyclic Redundancy Check*. Ele calcula um valor curto a partir de
uma sequencia de bytes. O receptor calcula o valor novamente e compara com o
valor recebido.

O CRC permite detectar muitos padroes de alteracao, mas nao reconstroi os bytes
originais. Tambem nao fornece autenticacao: um transmissor que consiga alterar
dados e recalcular o CRC nao e impedido por esse mecanismo.

### Parametros atuais

| Parametro | Valor |
|---|---|
| Width | 16 bits |
| Polynomial | `0x1021` |
| Init | `0xFFFF` |
| RefIn | `false` |
| RefOut | `false` |
| XorOut | `0x0000` |
| Check | `0x29B1` para `123456789` |
| Residue | `0x0000` |

No codigo, `crc16` esta em
[`protocol/crc.py`](../src/meshmedia_lab/protocol/crc.py). O `Packet` calcula o
CRC sobre `header + payload` e anexa o resultado como dois bytes em ordem de
rede. O receptor rejeita o pacote quando o valor nao confere. O vetor de
referencia e testado em
[`tests/unit/test_protocol.py`](../tests/unit/test_protocol.py).

### Por que documentar a tupla completa

O nome CCITT-FALSE e usado para identificar uma configuracao comum, mas nomes
de CRC podem ser usados de forma inconsistente. O polinomio, inicializacao,
reflexao e XOR final precisam ser registrados juntos. A implementacao nao deve
depender apenas do nome informal do algoritmo.

## 4. FEC

*Forward Error Correction* adiciona redundancia antes da transmissao. O
receptor usa a redundancia para recuperar dados sem solicitar o envio novamente.

FEC e uma categoria, nao um algoritmo unico. Exemplos incluem Hamming, BCH,
codigos convolucionais, LDPC, Polar e Reed-Solomon.

No MeshMedia Lab, FEC pode ser relevante quando o canal de retorno e caro, a
transmissao percorre varios saltos ou o custo de airtime de uma retransmissao e
maior que o custo de alguns simbolos de reparo. A redundancia, entretanto,
aumenta o numero de bytes e pode piorar a ocupacao do canal quando a perda e
baixa.

### 4.1 Contrato abstrato da Issue #19

A interface FEC deve ser independente do algoritmo. Ela pertence a uma camada
de laboratorio entre os dados codificados e a fragmentacao; nao deve obrigar o
protocolo a conhecer Reed-Solomon.

O contrato abstrato da Issue #19 foi materializado como uma API Python
independente de algoritmo em `src/meshmedia_lab/fec/`. A Issue #20 adiciona
uma implementacao standalone de Reed-Solomon sobre esse contrato. A camada
continua separada do protocolo MM1, do CRC, dos codecs e dos transportes.

Os tipos, validadores e protocolos estao em
[`src/meshmedia_lab/fec/contract.py`](../src/meshmedia_lab/fec/contract.py),
com exports controlados por `src/meshmedia_lab/fec/__init__.py`. O contrato e
testado por [`tests/unit/test_fec.py`](../tests/unit/test_fec.py) usando uma
implementacao fake, sem alegar recuperacao matematica.

A preparacao de uma transmissao completa esta em
`src/meshmedia_lab/fec/transmission.py`. Ela divide os bytes produzidos pelo
codec em blocos com capacidade `k * symbol_size`, chama o `FecEncoder` para
cada bloco e conserva a ordem, o indice do bloco e o
`FecBlockMetadata`. O caminho nao conhece pixels, pacotes ou transporte.

O contrato logico e:

```text
FecEncoder.encode(source_block, config)
    -> EncodedBlock(source_symbols, repair_symbols, metadata)

FecDecoder.decode(received_symbols, erasures, config, metadata)
    -> DecodeResult(source_block, recovered_symbols, success, reason)
```

O decoder recebe os metadados locais do bloco porque somente `config` nao
carrega o comprimento original necessario para remover padding. O contrato
continua recebendo o tipo local; no modo FEC, seus valores equivalentes sao
transportados pelo frame `FC` sem alterar o wire format legado.

Os contratos de encoder e decoder usarao `typing.Protocol`, seguindo as
interfaces estruturais existentes no projeto. Nao sera criada uma hierarquia
`ABC` paralela.

#### Configuracao

`FecConfig` deve conter, no minimo:

| Campo | Significado |
|---|---|
| `algorithm_id` | Identifica o algoritmo sem acoplar a classe concreta |
| `symbol_size` | Tamanho fixo de cada simbolo em bytes |
| `data_symbols` (`k`) | Quantidade de simbolos de origem |
| `repair_symbols` (`r`) | Quantidade de simbolos de reparo |
| `block_symbols` (`n`) | Quantidade total transmitida; normalmente `k + r` |
| `interleaving_depth` | Profundidade de intercalacao, ou zero |
| `padding_policy` | Regra para completar o ultimo bloco |
| `incomplete_block_policy` | Regra para bloco menor que `k` |

As politicas serao tipos explicitos:

- `PaddingPolicy.REJECT`: qualquer padding necessario rejeita o bloco;
- `PaddingPolicy.ZERO_PAD`: permite completar bytes com zero;
- `IncompleteBlockPolicy.REJECT`: rejeita menos de `k` simbolos de origem;
- `IncompleteBlockPolicy.PAD_TO_K`: completa o bloco ate `k` simbolos.

O comprimento original e a quantidade de padding serao preservados em
metadados locais imutaveis. No modo FEC integrado, as politicas tambem sao
transportadas no frame `FC` para permitir a validacao no RX.

Uma configuracao invalida deve falhar antes de codificar. Exemplos: simbolo
com tamanho zero, `k` zero, `r` negativo, `n` diferente de `k + r` quando o
algoritmo exigir essa relacao, ou bloco maior que os limites declarados.

#### Encoder

O encoder recebe um bloco de bytes de origem e produz simbolos de tamanho fixo.
O resultado deve distinguir:

- simbolos de origem, com indices `0..k-1`;
- simbolos de reparo, com indices `k..n-1`;
- bytes de padding adicionados ao ultimo bloco;
- metadados necessarios para remover o padding depois da recuperacao.

O encoder nao deve serializar pacotes MM1 nem calcular o CRC. A fragmentacao,
o envelope v1 e a integridade permanecem responsabilidades do protocolo.

#### Decoder

O decoder recebe simbolos identificados por indice e um conjunto de erasures
conhecidas. Um pacote ausente ou rejeitado pelo CRC pode entrar como erasure
quando o indice do simbolo for conhecido.

O resultado deve informar:

- se o bloco foi recuperado;
- bytes de origem, sem padding quando possivel;
- quantidade de simbolos recuperados;
- indices ausentes ou invalidos;
- motivo de falha quando houver dados insuficientes ou configuracao invalida.

O decoder nao deve tratar um simbolo corrompido como valido apenas porque a
posicao existe. Corrupcoes desconhecidas pertencem a um cenario separado do
experimento RS-only e precisam ser identificadas no resultado.

#### Blocos incompletos e limites

O comportamento do ultimo bloco deve ser escolhido por configuracao. As
alternativas sao rejeitar o bloco, preencher ate `k` simbolos ou usar uma
representacao explicita de comprimento. No modo FEC integrado, o valor adotado
aparece no frame `FC` e no registro do experimento.

Um decoder nao pode prometer recuperacao fora dos limites do algoritmo. Para
Reed-Solomon, a referencia classica e `2e + s <= n-k`, onde `e` sao erros
desconhecidos e `s` sao erasures conhecidas. Esse limite e de simbolos, nao de
bits.

#### Separacao de camadas

```mermaid
flowchart LR
    A[Bytes do codec] --> B[Particao em blocos]
    B --> C[Interface FEC]
    C --> D[Simbolos de origem e reparo]
    D --> E[Fragmentacao MM1 v1]
    E --> F[CRC por pacote]
    F --> G[Transporte]
    G --> H[Validacao CRC]
    H --> I[Decoder FEC]
    I --> J[Bytes de origem]
    J --> K[Reassemblagem e decoder de imagem]
```

A interface deve permitir Hamming, BCH, Reed-Solomon ou outro algoritmo sem
modificar o contrato do codec de imagem. A Issue #19 implementa o contrato e
suas validacoes; a Issue #20 implementa o algoritmo Reed-Solomon e as Issues
#21/#22 integram a preparacao e a recuperacao sem acoplar o pipeline a essa
classe concreta.

### 4.2.1 Extensao FEC opt-in no MM1 v1

O MM1 v1 legado continua com header de 19 bytes, CRC de 2 bytes e os mesmos
campos. A integracao FEC usa a flag nova `FLAG_FEC=0x08`, que nao reutiliza
`INLINE_DESCRIPTOR=0x04`. Essa flag seleciona uma extensao experimental que
exige um RX atualizado; ela nao transforma o caminho legado em FEC nem promete
interoperabilidade transparente com um RX antigo.

Cada pacote FEC carrega um `FecSymbolFrame` no payload. O frame usa o marcador
`FC`, versao `1` e repete os parametros necessarios para que a perda do primeiro
pacote nao esconda a configuracao:

| Campo | Funcao |
|---|---|
| `algorithm_id` | Identifica o encoder/decoder sem fixar a classe no contrato |
| `symbol_size`, `data_symbols`, `repair_symbols`, `block_symbols` | Configuracao do bloco |
| `interleaving_depth` e politicas | Reproduzem o `FecConfig` |
| `encoded_length`, `total_blocks` | Associam todos os blocos a uma transmissao |
| `block_index`, `symbol_index` | Identificam a posicao do simbolo |
| `original_length`, `padding_length` | Preservam o `FecBlockMetadata` local |
| `symbol_data` | Dados do simbolo de origem ou reparo |

O layout binario do frame e:

```text
magic(2) | frame_version(1) | algorithm_id_length(1)
| symbol_size(2) | data_symbols(2) | repair_symbols(2)
| block_symbols(2) | interleaving_depth(2)
| padding_policy(1) | incomplete_block_policy(1)
| encoded_length(4) | total_blocks(2) | block_index(2)
| original_length(4) | padding_length(4) | symbol_index(2)
| algorithm_id(N) | symbol_data(symbol_size)
```

O indice `0..k-1` identifica simbolos de origem; os indices restantes
identificam reparos. A implementacao inicial envia um simbolo por pacote.
`fragment_number` continua sendo o numero do fragmento MM1 e segue a ordem
`block_index * n + symbol_index`; `total_fragments` e `total_blocks * n`.

O frame FEC fica dentro do payload normal do pacote MM1, portanto o CRC
continua cobrindo header e payload. Um pacote rejeitado pelo CRC desaparece
antes da camada FEC e sua posicao esperada e tratada como erasure. Uma
alteracao que passe pelo CRC continua sendo um erro desconhecido e fica sujeita
aos limites matematicos do Reed-Solomon.

O Transmission Descriptor v1 nao foi alterado. Quando usado junto com FEC, o
prefixo `TD` permanece no primeiro payload e o frame FEC vem depois dele; os
parametros FEC continuam no frame FEC, nao no corpo do descritor.

### FEC, retransmissao e CRC

| Mecanismo | Recupera dados? | Precisa de retorno? | Custo principal |
|---|---:|---:|---|
| CRC | Nao | Nao | Bytes de integridade e descarte de pacotes invalidos |
| FEC | Pode recuperar | Nao | Redundancia, memoria e processamento |
| Retransmissao seletiva | Sim | Sim | ACK/NACK, tempo e airtime adicional |
| FEC + retransmissao | Sim | Opcional | Complexidade e custos combinados |

## 5. Reed-Solomon

Reed-Solomon e um codigo de bloco definido sobre um campo finito. Uma
configuracao `[n,k]` transforma `k` simbolos de dados em `n` simbolos
transmitidos. Os `n-k` simbolos adicionais sao simbolos de reparo.

Quando os simbolos sao elementos de `GF(2^8)`, cada elemento pode ser
representado por um byte. Isso nao significa que todo pacote tenha um byte de
payload: um simbolo de rede pode ser um vetor fixo de bytes, desde que o
algoritmo e o preenchimento sejam definidos.

Para `e` erros de simbolo desconhecidos e `s` erasures conhecidas, a condicao
classica e:

```text
2e + s <= n - k
```

Se somente existem erasures e as posicoes ausentes sao conhecidas, o limite e
`s <= n-k`. Em um codigo sistematico MDS, qualquer conjunto de `k` simbolos
validos pode recuperar o bloco de origem, desde que os simbolos invalidos ou
ausentes sejam identificados.

### Matriz experimental inicial

As configuracoes abaixo sao pontos de partida para medir o custo e a
recuperacao. Elas nao sao ainda uma escolha definitiva do protocolo.

| Codigo | Dados | Reparos | Taxa `k/n` | Erasures | Erros desconhecidos | Reparos/dados |
|---|---:|---:|---:|---:|---:|---:|
| RS(32,28) | 28 | 4 | 87,5% | 4 | 2 | 14,3% |
| RS(32,24) | 24 | 8 | 75,0% | 8 | 4 | 33,3% |
| RS(32,20) | 20 | 12 | 62,5% | 12 | 6 | 60,0% |

Os limites de erro da tabela sao limites de simbolos, nao necessariamente de
bits. A matriz deve ser repetida com uma definicao explicita de tamanho do
simbolo, tamanho do bloco, preenchimento e forma de transportar os simbolos.

O [RFC 5510](references.md#rfc5510) especifica esquemas Reed-Solomon para
canal de erasure e mostra a separacao entre simbolos de origem, simbolos de
reparo, tamanho do simbolo e bloco de origem. Esses conceitos sao referencia
para o experimento, nao uma afirmacao de que o MeshMedia Lab ja implementa o
RFC.

### 5.1 Definicao tecnica da Issue #20

A primeira implementacao concreta sera um experimento standalone, sem
integracao com MM1, CRC ou transporte. A convencao matematica e:

| Parametro | Decisao |
|---|---|
| Campo finito | `GF(2^8)` |
| Polinomio primitivo | `x^8 + x^4 + x^3 + x^2 + 1` (`0x11D`) |
| Elemento gerador | `alpha = 0x02` |
| Representacao do elemento | Um byte (`0x00..0xFF`) |
| Tamanho do simbolo | `symbol_size=1` byte |
| Comprimento maximo | `n <= 255` |
| Interleaving | Desabilitado (`interleaving_depth=0`) |
| Identificador | `algorithm_id="reed_solomon"` |
| Dependencias | Somente a biblioteca padrao Python |

Os pontos de avaliacao sao `x_i = alpha^i`, para `i` entre `0` e `n-1`.
O encoder interpola um polinomio `P(x)` de grau menor que `k` a partir dos
simbolos de origem nas posicoes `0..k-1`. Os simbolos de reparo sao as
avaliacoes de `P(x)` nas posicoes `k..n-1`. Assim, o codigo e sistematico:
os simbolos de origem permanecem inalterados e os indices identificam
deterministicamente as posicoes do codeword.

O bloco de origem possui capacidade `k` bytes. Quando permitido por
`PaddingPolicy.ZERO_PAD` e `IncompleteBlockPolicy.PAD_TO_K`, bytes zero
completam o bloco; `FecBlockMetadata` preserva o comprimento original e e
repetido no frame `FC` durante a integracao. `PaddingPolicy.REJECT` e
`IncompleteBlockPolicy.REJECT` continuam sendo aplicadas pelo contrato.

O decoder trata todas as posicoes ausentes como erasures e tambem aceita erros
desconhecidos nas posicoes recebidas. A recuperacao somente e declarada quando
`2e + s <= n-k`; acima desse limite, ou quando nao existe um codeword valido
consistente com os simbolos recebidos, o resultado e uma falha sem
`source_block` parcial. A implementacao concreta rejeita configuracoes com
`symbol_size` diferente de `1` ou interleaving diferente de zero, em vez de
atribuir semantica nao documentada a esses campos.

Essa definicao fecha a representacao matematica da Issue #20. A extensao
experimental das Issues #21/#22 usa a flag `FLAG_FEC=0x08` e frames `FC`
descritos na secao 4.2.1, sem alterar o layout do header, o CRC ou o corpo do
Transmission Descriptor v1.

O vetor independente fixado para a codificacao e `k=4`, `r=3`, origem
`01 02 03 04` e codeword completo
`01 02 03 04 D6 36 E2`. Os tres ultimos bytes sao os simbolos de reparo;
esse valor e verificado diretamente em
`tests/unit/test_reed_solomon.py`, sem gerar a expectativa a partir do
encoder sob teste.

## 6. Camada integrada para o protocolo

Uma arquitetura candidata para um canal orientado a pacotes e:

```text
bytes codificados
  -> bloco de simbolos de origem
  -> Reed-Solomon
  -> simbolos de origem + reparo
  -> pacote individual com cabecalho e CRC
  -> canal
```

No receptor:

```text
pacote recebido
  -> validar CRC
  -> aceitar simbolo ou marcar erasure
  -> agrupar por bloco FEC
  -> decodificar Reed-Solomon
  -> reassemblar bytes de origem
```

Essa ordem e a implementacao experimental atual. Ela trata um pacote perdido ou
rejeitado pelo CRC como uma erasure conhecida. O frame FEC identifica bloco,
simbolo, configuracao e metadados locais, enquanto o envelope MM1 continua
responsavel por sequenciamento e CRC.

O modo sem FEC permanece o default e usa somente os caminhos legados ou com
descritor ja existentes. O modo FEC e explicitamente opt-in e nao deve ser
enviado a um RX que nao conheca `FLAG_FEC=0x08`.

## 7. Plano de afericao

As Issues #21/#22 adicionam testes locais de preparacao, packetizacao,
reassemblagem, perdas e recuperacao para grayscale e RGB332. Esses testes
demonstram a integracao funcional, mas nao sao benchmarks de radio e nao
selecionam uma configuracao de producao.

Cada configuracao deve ser comparada com uma mesma imagem, codec, resolucao,
quantizacao, tamanho de payload e semente de simulacao. A comparacao inicial
deve incluir:

- baseline sem FEC;
- RS(32,28), RS(32,24) e RS(32,20);
- perda aleatoria de 5%, 10%, 20% e 30%;
- perda em rajadas;
- corrupcao de pacotes separada de perda;
- posicoes de fragmentos ausentes conhecidas;
- retransmissao seletiva quando ela for implementada;
- combinacao de FEC e retransmissao quando ambas existirem.

As metricas obrigatorias sao:

| Metrica | Objetivo |
|---|---|
| Imagens reconstruidas | Medir sucesso fim a fim |
| Simbolos recuperados | Medir a capacidade do FEC |
| Bytes de origem | Medir dados uteis |
| Bytes de reparo | Medir redundancia |
| Bytes totais | Medir custo de transmissao |
| Numero de pacotes | Medir o impacto no transporte |
| Overhead de cabecalho e CRC | Separar custo de integridade |
| Airtime estimado | Medir ocupacao do canal |
| Tempo de codificacao | Medir custo no transmissor |
| Tempo de decodificacao | Medir custo no receptor |
| Memoria utilizada | Avaliar buffers necessarios |
| Latencia total | Avaliar experiencia de uso |
| Taxa de falha | Medir casos sem recuperacao |

Os experimentos devem registrar a semente, a configuracao completa e o numero
de repeticoes. Resultados sem esses dados nao devem ser tratados como
comparaveis.

O conjunto minimo de cenarios, payloads, dimensoes e ambientes esta detalhado
em [`experiment-matrix.md`](experiment-matrix.md). O modo RS-only descrito ali
e somente um harness controlado e nao um modo do MM1 v1.

## 8. Limites e decisoes em aberto

- O CRC atual detecta corrupcao, mas nao autentica o remetente.
- A implementacao standalone usa simbolos de um byte; vetores de simbolos
  permanecem fora desta primeira variante.
- A implementacao atual usa simbolos de um byte em frames FEC, um simbolo por
  pacote, e identifica reparos pelo indice `k..n-1`.
- A extensao FEC nao e uma recomendacao de producao; seu custo de overhead
  deve ser medido antes de escolher parametros.
- O impacto de perdas em rajada e intercalacao ainda precisa ser medido.
- O custo real de airtime depende do transporte MeshCore e nao do UDP local.
- Nenhuma configuracao RS deve ser chamada de recomendada para producao antes
  dos experimentos.

## Referencias

- [Reed e Solomon, 1960](references.md#rs60)
- [RFC 5510](references.md#rfc5510)
- [Hamming, 1950](references.md#hamming50)
- [Koopman e Chakravarty, 2004](references.md#koopman2004)
