# Transmission Descriptor no MM1 v1

Contrato da extensao inline da Issue #17, conforme ADR 0004. O estado de entrega
esta em `implementation-status.md`. Nenhum header, campo existente, FIRST/LAST
ou algoritmo CRC e removido ou reinterpretado.

## 1. Envelope e selecao explicita

O header continua big-endian com 19 bytes:

```text
offset  tamanho  campo
0       2        magic = "MM"
2       1        protocol_version = 1
3       1        media_type
4       1        codec
5       1        flags
6       2        image_id / transmission_id
8       2        fragment_number
10      2        total_fragments
12      2        width
14      2        height
16      2        levels
18      1        payload_length
19      P        payload
19 + P  2        CRC-16/CCITT-FALSE(header + payload)
```

Flags `FIRST_FRAGMENT=0x01`, `LAST_FRAGMENT=0x02` e a extensao explicitamente
registrada `INLINE_DESCRIPTOR=0x04`. Esta ultima aparece em **todos** os pacotes
estendidos. Flags esperadas: unico `0x07`, primeiro `0x05`, meio `0x04`,
ultimo `0x06`. Flags desconhecidas ou FIRST/LAST incoerentes invalidam o modo
estendido. A validacao historica do modo legado permanece inalterada.

Sem `0x04`, o payload inteiro e dado legado, mesmo comecando por "TD".
Com `0x04`, o prefixo e obrigatorio no fragmento numero zero; qualquer erro
invalida a transmissao, sem fallback. Nos demais fragmentos todos os bytes sao
dados, inclusive quando comecam por "TD". Nao ha varredura de marcadores.

## 2. Prefixo e corpo do descritor

```text
fragmento 0: [header][54 44][10][corpo v1, 16 bytes][dados_0][CRC]
demais:     [header][dados_i][CRC]
```

`descriptor_length` e uint8, mede apenas o corpo. Nesta versao deve ser **16**,
nao zero, nem maior. A capacidade fisica do campo e 255, mas isso nao autoriza
corpos maiores. O prefixo inteiro tem 19 bytes e deve caber no primeiro payload.
Inteiros multibyte usam big-endian; endianess nao se aplica aos campos uint8.

Offsets relativos ao inicio do **corpo**, isto e, payload offset 3:

| Offset | Bytes | Campo | Regra v1 |
|---:|---:|---|---|
| 0 | 1 | descriptor_version | `1`; desconhecida rejeitada |
| 1 | 1 | descriptor_flags | `0`; bits reservados rejeitados |
| 2 | 1 | media_type | `0x01` IMAGE |
| 3 | 1 | codec | `0x01` grayscale, `0x02` RGB332 |
| 4 | 2 | width | Grayscale `1..128`, RGB332 `1..64` |
| 6 | 2 | height | Independente de width; mesmos limites |
| 8 | 2 | levels | Grayscale `2,4,8,16,256`; RGB332 `0` |
| 10 | 4 | encoded_length | Obrigatorio, nao inclui descritor/header/CRC |
| 14 | 1 | compression_id | `0` NONE; outros rejeitados |
| 15 | 1 | codec_parameters_length | `0`; parametros extras nao suportados |

Nao e TLV: nao ha campos opcionais/repetidos. Campos ausentes, corpo excedente
ou parametros extras sao invalidos, nao ignorados. `levels` parametriza
grayscale; RGB332 identifica profundidade fixa RRRGGGBB. FEC e compressao futura
nao sao implicitamente habilitados nem possuem campos neste corpo.

O descritor repete media_type, codec, width, height e levels para autodescricao,
**substituindo a proposta anterior da Etapa A que evitava duplicacao**. Todos
devem coincidir com cada header MM1. O RX usa os metadados validados do descritor
para decodificar; nunca escolhe um lado de uma inconsistencia. `image_id` e
contadores permanecem unicamente no header. Protocolo e descritor possuem
versoes independentes; este corpo exige protocolo MM1 `1`.

## 3. Comprimento e fragmentacao

Sem compressao ou FEC, exigir:

```text
grayscale: encoded_length = ceil(width * height * log2(levels) / 8)
RGB332:    encoded_length = width * height
```

Esse calculo e uma validacao do contrato, nao uma inferencia de codec a partir
do tamanho recebido. Limites atuais: 16384 bytes grayscale (256 niveis),
4096 RGB332. Valores zero, enormes ou inconsistentes sao rejeitados antes de
alocar imagem ou buffer proporcional ao comprimento declarado.

TX seleciona explicitamente `legacy` (default) ou `descriptor`.
Para `D=19`, `P` limite do payload e `L` comprimento codificado:

```text
P < D: erro no TX, nenhum pacote enviado (descritor nao e dividido)
P = D: fragmento zero so com descritor; dados comecam no fragmento 1
P > D: ate P-D bytes de imagem no fragmento zero
fragment_count = ceil((L + D) / P)
wire_bytes = L + D + 21 * fragment_count
```

Todos os fragmentos depois do zero possuem pelo menos um byte de dado. Nao ha
padding de fragmento. Com `P=64`:

| Caso | L | Legado | Descritor | Bytes MM1 com descritor |
|---|---:|---:|---:|---:|
| Grayscale 16, 32x32 | 512 | 8 | 9 | 720 |
| RGB332, 32x32 | 1024 | 16 | 17 | 1400 |
| RGB332, 64x64 | 4096 | 64 | 65 | 5480 |

Overhead do descritor e contabilizado separadamente do header/CRC; soma dos
payloads inclui descritor. Nenhum valor desta tabela representa radio real.

## 4. RX, ordem e limites de recursos

1. Validar envelope, tamanho e CRC antes de interpretar descritor.
2. Selecionar modo pela flag. Associar uma transmissao por reassembler usando
   image_id, total_fragments, metadata e modo constantes.
3. No modo estendido, validar metadata do header mesmo antes do fragmento zero.
   A quantidade de fragmentos nao pode exceder `L+1` (cada fragmento posterior
   tem dado nao vazio; o zero pode conter so descritor). Nunca prealocar a partir
   de total_fragments ou encoded_length recebido.
4. Armazenar dados fora de ordem em dicionario incremental, no maximo `L` bytes
   uteis e `L+1` entradas; L e calculado dos metadados limitados, nao confiado
   cegamente ao uint32 recebido. O descritor e validado antes de armazenar
   dados do fragmento zero. Nao alocar pixels/decodificar sem descritor valido.
5. Remover o prefixo somente do zero. Duplicata identica e idempotente; comparar
   tambem o descritor nas duplicatas do zero. Duplicata conflitante, troca de modo,
   metadata ou contadores invalida a transmissao estendida.
6. Soma final deve ser exatamente encoded_length; fragmentos faltantes ou
   dados a menos/a mais nunca produzem uma imagem. `is_complete` so e verdadeiro
   com todos os fragmentos e descritor valido.
7. Uma falha de reassemblagem estendida e terminal: liberar fragmentos e impedir
   assemble/novos adds nessa instancia. Uma nova transmissao usa nova instancia.
   Pacote de outro image_id e descartado sem destruir a transmissao corrente.

O reassembler nao possui relogio. Timeout permanece responsabilidade do chamador;
RX CLI usa `--timeout` de inatividade (default 30 s). Nao ha multiplexacao,
timeout absoluto, identificacao autenticada do emissor ou recuperacao por FEC.
Pacote rejeitado por CRC nao fornece indice confiavel de erasure.

## 5. Compatibilidade e historico

| TX | RX atualizado | RX legado |
|---|---|---|
| Legado | Aceito; sem inspecionar marcador | Baseline inalterado |
| Descritor | Valida flag e descritor | Nao compativel |

Receptores antigos podem ignorar flags desconhecidas e tentar decodificar o
prefixo. Nao ha deteccao/negociacao automatica de capacidades: enviar descritor
somente para RX conhecido. O modo legado mantem exatamente os vetores binarios,
APIs e default. Nao ha promessa de interoperabilidade transparente.

ADR 0004 registra a troca da proposta preliminar (sem campos duplicados, length
opcional, magic indefinido) pelo contrato atual aprovado para implementacao.
O protocolo continua MM1 v1 com extensao opt-in; nao e chamado de v2.
FEC, Reed-Solomon e outros formatos permanecem propostos; nao cabem implicitamente
nesta versao. Nao se deve alterar este corpo silenciosamente para acrescenta-los.

## 6. Vetores fixos

Prefixos completos, sem header MM1/CRC:

```text
grayscale 2x2, levels=16, encoded_length=2:
54 44 10 01 00 01 01 00 02 00 02 00 10 00 00 00 02 00 00

RGB332 2x1, levels=0, encoded_length=2:
54 44 10 01 00 01 02 00 02 00 01 00 00 00 00 00 02 00 00
```

Pacotes completos de referencia: grayscale 2x2, levels 16, image_id 7,
dados `08 f4`, limite de payload 64, incluindo CRC:

```text
legado (23 bytes):
4d 4d 01 01 01 03 00 07 00 00 00 01 00 02 00 02 00 10 02 08 f4 2c ee

descritor (42 bytes):
4d 4d 01 01 01 07 00 07 00 00 00 01 00 02 00 02 00 10 15
54 44 10 01 00 01 01 00 02 00 02 00 10 00 00 00 02 00 00 08 f4 b7 23
```

Mutacoes negativas a fixar em testes: marcador `58 44`; comprimento `0f`/`11`/
`ff`; corpo truncado em cada offset; versao `02`; flags `01`; codec `ff`;
media `02`; dimensoes zero ou acima dos limites; levels grayscale `32` ou
RGB332 `16`; encoded_length `0`/`ffffffff`; compression `01`; parametros `01`.
Tambem testar prefixo duplicado como corpo excedente, header/descritor
divergentes, FIRST/LAST invalidos, mistura de modos, fragmento zero ausente,
duplicata conflitante e comprimento final menor/maior.
