# Perfil de transmissao MM1 v1

Este documento define os parametros explicitos de uma transmissao de imagem e
separa o modo legado MM1 v1 da extensao inline opt-in especificada no ADR 0004.

**Estado:** RGB332 foi aprovado como codec da implementacao de referencia apos
os testes locais de `32x32` e `64x64`. A integracao usa os campos existentes do
MM1 v1, sem alterar o cabecalho de 19 bytes ou criar um descritor obrigatorio.

## 1. Escopo e estados

O perfil nao e um catalogo de presets. O transmissor deve informar ou registrar
os valores efetivamente usados em cada transmissao e experimento.

| Item | Estado |
|---|---|
| MM1 v1 sem descritor | Implementado como baseline local |
| Grayscale packed | Implementado com codec `0x01` |
| Limite de 128 x 128 | Implementado no grayscale; nao inclui tiling |
| Descritor inline no primeiro fragmento | Implementado localmente como extensao opt-in v1; ADR 0004 |
| RGB332 | Implementado no codec e no envelope MM1 v1 |
| Contrato FEC parametrizavel | Implementado; RS standalone experimental sem integracao |
| Perfis nomeados ou presets | Futuro; fora desta etapa |

O protocolo continua sendo MM1 v1. O descritor nao cria uma v2 e nao altera o
cabecalho v1 existente. Ele e uma extensao opcional que exige um receptor capaz
de interpretar o primeiro payload no modo com descritor.

## 2. Parametros da transmissao

Os parametros abaixo formam o perfil logico de uma transmissao. Os tamanhos da
tabela sao tipos candidatos para a extensao; no pacote v1 legado, os tamanhos
efetivos sao os definidos pelo cabecalho existente em
`src/meshmedia_lab/protocol/packet.py`.

| Parametro | Tipo logico | Regra inicial | Situacao |
|---|---|---|---|
| `transmission_id` (`image_id` no v1) | `uint16` | `0..65535` | Implementado |
| `media_type` | `uint8` | `0x01 = IMAGE` | Implementado |
| `codec_id` | `uint8` | `0x01` grayscale; `0x02` RGB332 | Implementado para os codecs atuais; registro extensível ainda parcial |
| `width` | `uint16` no v1 | Grayscale `1..128`; RGB332 `1..64`, independente de `height` | Implementado com limite por codec |
| `height` | `uint16` no v1 | Grayscale `1..128`; RGB332 `1..64`, independente de `width` | Implementado com limite por codec |
| `levels` | `uint16` no v1 | Grayscale: niveis validos; RGB332: `0` (nao aplicavel) | Implementado por codec |
| `codec_parameters` | bytes versionados | Comprimento zero no descritor v1; levels parametriza grayscale | Implementado vazio; extras rejeitados |
| `encoded_length` | `uint32` big-endian no descritor | Obrigatorio e igual ao tamanho derivado do codec | Implementado no modo descriptor |
| `total_fragments` | `uint16` | Pelo menos 1 | Implementado no v1 |
| `payload_limit` | `uint8` no v1 | `1..255` local; limite externo pode ser menor | Implementado |
| `compression_id` | `uint8` no descritor | Apenas `0=NONE`; outros rejeitados | Implementado NONE |
| `fec_config` | estrutura explicita | Sem FEC no baseline | Contrato abstrato implementado; integracao proposta |

`width` e `height` nao formam uma proporcao obrigatoria. Imagens retangulares
sao validas. A area maxima inicial e, portanto, `128 x 128`; nao ha tiling nem
composicao automatica de imagens maiores nesta fase.

O limite de 128 pixels e aplicado independentemente a largura e a altura por
`ImageMetadata`, `ImageEncoder` e `EncodedImage`. Dimensoes maiores sao
rejeitadas antes de criar ou aceitar uma representacao grayscale. A regra nao
introduz tiling nem altera os campos de duas bytes do cabecalho MM1 v1.

## 3. Registro de codecs

### 3.1 Grayscale packed

| Campo | Valor |
|---|---|
| `codec_id` | `0x01` |
| Entrada | Matriz de pixels grayscale de 8 bits |
| Ordem | Row-major, da primeira linha para a ultima |
| Quantizacao | `q = floor(pixel * levels / 256)` |
| Niveis | `2`, `4`, `8`, `16` ou `256` no encoder atual |
| Empacotamento | Bits mais significativos primeiro dentro do fluxo |
| Padding final | Bits restantes preenchidos com zero |
| Compressao | Nenhuma; RLE nao esta ativo |
| Tamanho derivavel | `ceil(width * height * log2(levels) / 8)` bytes |

O valor quantizado ocupa `log2(levels)` bits por pixel. O decoder atual
reconstroi os valores para a escala `0..255` usando os niveis recebidos.

Para este codec, `width`, `height` e `levels` ja estao no cabecalho v1 atual.
A revisao da Issue #17 (ADR 0004) substitui a proposta preliminar da Etapa A:
o descritor os repete e exige igualdade, com `encoded_length` obrigatorio,
mesmo derivavel. Essa redundancia permite validacao e autodescricao.

O identificador `0x01` e parte do baseline implementado. A lista exata de
niveis aceitos pelo perfil permanece alinhada ao encoder implementado.

### 3.2 RGB332

Esta secao define o contrato RGB332 aprovado a partir da Issue #38. RGB332 e
um codec oficial da implementacao de referencia e pode ser selecionado pelas
aplicacoes locais. A integracao usa o envelope MM1 v1 existente; nenhum campo,
tamanho ou ordem do cabecalho foi alterado.

| Campo | Valor |
|---|---|
| `codec_id` | `0x02` implementado |
| Tamanho | 1 byte por pixel |
| Ordem dos bits | `RRRGGGBB` |
| Ordem dos canais | Vermelho, verde, azul |
| Ordem dos pixels | Row-major |
| Alpha | Nao presente |
| Tamanho derivavel | `width * height` bytes |
| Compressao | Nenhuma nesta etapa |

O identificador `0x02` e o identificador implementado para RGB332. No cabecalho
MM1 v1, `levels=0` significa que a profundidade nao se aplica ao RGB332; os
bits `3/3/2` sao fixos pelo identificador do codec. Um receptor que nao conhece
`0x02` deve rejeitar o codec, sem tentar decodifica-lo como grayscale.

#### Quantizacao experimental

Cada canal de entrada e um inteiro em `0..255`. A quantizacao aprovada para o
experimento e a mesma politica de piso usada pelo grayscale:

```text
r3 = floor(red   * 8 / 256)
g3 = floor(green * 8 / 256)
b2 = floor(blue  * 4 / 256)

byte = (r3 << 5) | (g3 << 2) | b2
```

Assim, `r3` e `g3` pertencem a `0..7` e `b2` pertence a `0..3`. O encoder usa
resize por amostragem inteira, com a mesma regra do grayscale, antes de
quantizar. A entrada experimental e uma matriz de pixels RGB; alpha nao faz
parte da representacao e deve ser rejeitado pela API isolada.

O decoder reconstrui os valores usando tabelas fixas e deterministicas:

```text
3 bits: [0, 36, 73, 109, 146, 182, 219, 255]
2 bits: [0, 85, 170, 255]
```

Essa escolha preserva os extremos e permanece alinhada ao decoder grayscale.
Ela pode ser substituida em experimento posterior, desde que a politica de
quantizacao e reconstrucao seja versionada e registrada nos resultados.

O limite RGB332 nesta implementacao e de 64 pixels por dimensao. Os cenarios
avaliados nesta Issue sao `32x32` e `64x64`; `128x128` nao faz parte desta
rodada. A API aceita dimensoes independentes dentro de `1..64`, sem introduzir
tiling ou alterar o limite global documentado para o grayscale.

As aplicacoes locais recebem `--codec grayscale|rgb332`. O default permanece
`grayscale` para preservar o comportamento anterior. `--levels` e usado
somente pelo grayscale; RGB332 usa sempre `levels=0` no metadata do pacote.

## 4. Controle de compressao

Codec, empacotamento e compressao sao conceitos separados.

| `compression_id` candidato | Significado | Estado |
|---:|---|---|
| `0x00` | Nenhuma compressao | Baseline atual |
| `0x01` | RLE | Futuro; nao implementado |

Um receptor nao deve inferir RLE apenas pelo tamanho do payload. Quando uma
compressao for introduzida, ela devera ser identificada explicitamente e ter
parametros documentados.

## 5. FEC no perfil

O perfil reserva uma configuracao explicita para controle de erros, mas nao
habilita FEC no MM1 v1 atual.

| Campo | Tipo candidato | Regra |
|---|---|---|
| `fec_algorithm` | `uint8` | `0x00 = NONE`; outros valores exigem suporte anunciado |
| `symbol_size` | `uint16` | Tamanho em bytes de um simbolo |
| `data_symbols` (`k`) | `uint16` | Simbolos de origem por bloco |
| `repair_symbols` (`r`) | `uint16` | Simbolos de reparo por bloco |
| `block_symbols` | `uint16` | Normalmente `k + r` |
| `interleaving_depth` | `uint16` | `0` quando desabilitado |
| `padding_policy` | `uint8` | Regra explicita para o ultimo bloco |
| `incomplete_block_policy` | `uint8` | Regra para blocos incompletos |

Esses campos sao apenas proposta para uma revisao futura: o corpo v1 do
descritor implementado nao os transporta e nao habilita FEC. A baseline segue
`fec_algorithm=none`, sem bytes de reparo. Reed-Solomon standalone e um
experimento implementado, nao uma recomendacao de producao nem uma
funcionalidade do protocolo.

CRC e FEC continuam sendo camadas diferentes:

- CRC detecta corrupcao no pacote e pode fazer o pacote ser tratado como
  erasure por um futuro decoder FEC.
- FEC adiciona redundancia e pode recuperar dados dentro de seus limites.
- Desabilitar CRC para o experimento RS-only nao altera o MM1 v1; esse modo
  pertence apenas ao harness controlado dos benchmarks.

## 6. Limites de payload e contagem de mensagens

O campo `payload_length` v1 tem um byte e o `Fragmenter` local aceita ate 255
bytes. Isso nao e o limite do transporte MeshCore.

Para `GRP_DATA`, a referencia atual usa 165 bytes de dados de aplicacao. Como
um pacote MM1 v1 ocupa `P + 19 + 2`, o limite conservador e:

```text
P + 21 <= 165
P <= 144
```

O valor padrao local e `P=64`.

No modo com descritor, o primeiro payload e dividido entre a extensao e os
dados. Se `D` for o tamanho do prefixo do descritor:

```text
dados_no_primeiro_fragmento <= payload_limit - D
```

No descritor v1, `D=19`. O TX rejeita `payload_limit < 19`; exatamente 19
permite fragmento zero somente com descritor. A contagem e
`ceil((encoded_bytes + 19) / payload_limit)` e pode acrescentar um fragmento.
Contabilizar descritor separadamente dos bytes uteis e do envelope MM1.

### 6.1 Cenario RGB332 da Issue #38

O experimento usa memoria e pode usar um harness UDP localhost para validar o
round-trip entre dois processos. Os datagramas do harness nao sao pacotes MM1;
o payload de referencia e `64` bytes e o overhead do envelope MM1 e calculado
separadamente, sem descritor e sem o envelope externo MeshCore:

```text
fragmentos = ceil(encoded_bytes / 64)
header_bytes = fragmentos * 19
crc_bytes = fragmentos * 2
overhead_mm1 = header_bytes + crc_bytes
wire_bytes = encoded_bytes + overhead_mm1
```

O baseline principal e grayscale packed com `16` niveis, escolhido pelo menor
custo de transporte e por ser o default atual das aplicacoes locais. O valor de
`levels` continua parametrizavel para uma comparacao posterior com `256` niveis.

## 7. Modos de transmissao

### Modo legado

O payload do primeiro fragmento inicia diretamente com dados codificados.
Todos os pacotes seguem o formato implementado atualmente.

### Modo com descritor inline

O primeiro fragmento inicia com um marcador, um comprimento e o corpo do
descritor. O restante do payload contem dados codificados. Os fragmentos
seguintes continuam usando o envelope v1 atual.

```mermaid
flowchart LR
    A[Imagem] --> B[Codec e parametros explicitos]
    B --> C[Descritor compacto]
    B --> D[Dados codificados]
    C --> E[Payload do fragmento 0]
    D --> E
    E --> F[Header MM1 v1 + CRC]
    D --> G[Fragmentos 1..N]
    F --> H[Transporte]
    G --> H
    H --> I[Receptor v1 com suporte a extensao]
    I --> J[Valida descritor]
    J --> K[Remove prefixo]
    K --> L[Reassemblagem]
    L --> M[Decoder]
```

O modo com descritor e uma extensao opt-in v1 selecionada por
`--transmission-mode descriptor` no TX. A flag `INLINE_DESCRIPTOR=0x04` em
todos os fragmentos identifica o modo, sem heuristicas no RX. O prefixo
`TD | 16 | corpo` esta somente no fragmento zero. Um receptor legado nao e
compativel. O modo legado permanece default, sem alteracao de bytes.

## 8. Valores desconhecidos e compatibilidade

- Um codec desconhecido deve ser rejeitado antes da decodificacao.
- Um algoritmo FEC desconhecido deve impedir o modo FEC, sem ser tratado como
  `NONE`.
- Parametros fora dos limites devem invalidar a transmissao.
- A versao do descritor deve ser validada separadamente da versao do protocolo.
- O valor `1` do protocolo continua identificando MM1 v1.
- Nenhum campo existente pode ganhar novo significado sem uma decisao de
  extensao registrada e testes de vetores binarios.
- Uma mudanca que remova metadados do cabecalho atual nao pertence a esta
  extensao e exigiria uma decisao de compatibilidade posterior.

## 9. O que nao e um perfil nesta etapa

Nao sao perfis aprovados:

- `32x32 grayscale 16 levels`;
- RS(32,28), RS(32,24) ou RS(32,20);
- qualquer combinacao de payload, codec e FEC chamada de recomendada;
- parametros do radio MeshCore;
- uma configuracao de airtime.

Esses valores podem ser cenarios de experimento, mas a transmissao deve
registrar cada parametro explicitamente.
