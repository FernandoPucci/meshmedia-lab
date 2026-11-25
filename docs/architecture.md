# Arquitetura do laboratorio

O laboratorio usa o layout `src/` para separar o pacote Python do codigo de
teste e dos artefatos experimentais. As fases do SDD descrevem a ordem de
evolucao; elas nao criam acoplamento entre as pastas.

As aplicacoes de teste local ficam fora do pacote principal. Elas simulam o
ambiente de uso sem transformar Pillow ou UDP em dependencias obrigatorias do
codec.

## Mapeamento do SDD

| Componente do SDD | Localizacao |
|---|---|
| Image Source | `src/meshmedia_lab/application/source.py` |
| Encoder | `src/meshmedia_lab/codec/encoder.py` |
| Decoder | `src/meshmedia_lab/codec/decoder.py` |
| Codec RGB332 | `src/meshmedia_lab/codec/rgb332.py` |
| Fragmenter | `src/meshmedia_lab/protocol/fragmenter.py` |
| Reassembler | `src/meshmedia_lab/protocol/reassembler.py` |
| CRC | `src/meshmedia_lab/protocol/crc.py` |
| Contrato FEC abstrato | `src/meshmedia_lab/fec/contract.py` |
| Preparacao FEC | `src/meshmedia_lab/fec/transmission.py` |
| Packet/Header | `src/meshmedia_lab/protocol/packet.py` |
| Frames e reassemblagem FEC | `src/meshmedia_lab/protocol/fec.py` |
| Transmitter | `src/meshmedia_lab/transport/transmitter.py` |
| Receiver | `src/meshmedia_lab/transport/receiver.py` |
| Transport Adapter | `src/meshmedia_lab/transport/adapter.py` |
| Channel Simulator | `src/meshmedia_lab/simulation/channel.py` |
| Pipeline da aplicacao | `src/meshmedia_lab/application/pipeline.py` |
| UDP local | `src/meshmedia_lab/transport/udp.py` |
| Reed-Solomon standalone | `src/meshmedia_lab/fec/reed_solomon.py` |
| Aplicacao TX | `apps/local/tx.py` |
| Aplicacao RX | `apps/local/rx.py` |
| Integracao Pillow | `apps/local/image_io.py` |
| Perfil de transmissao | `docs/transmission-profile.md` |
| Transmission Descriptor | `docs/transmission-descriptor.md` |
| Modelo/parser do descritor | `src/meshmedia_lab/protocol/descriptor.py` |
| Matriz de experimentos | `docs/experiment-matrix.md` |
| Experimento RGB332 | `benchmarks/rgb332_experiment.py` |
| Executor Issue #24 | `benchmarks/issue24/` e `benchmarks/issue24_experiment.py` |
| Artefatos Issue #24 | `experiments/issue-24/` |
| WebApp PoC BLE/texto | `web/` |

## Limites

- `codec` transforma imagens em uma representacao binaria e a reconstrui.
- `protocol` conhece a organizacao dos pacotes, mas nao conhece radio.
- `transport` envia e recebe bytes por uma interface substituivel.
- `simulation` injeta as condicoes de um canal sem alterar o protocolo.
- `application` coordena os componentes, sem implementar seus detalhes.
- `apps/local` fornece executaveis de validacao, sem ser parte do codec.
- O codec RGB332 aprovado usa o envelope MM1 v1 existente; o harness UDP
  experimental continua disponivel apenas para validacao local separada.

## Fluxo TX/RX local

```text
Arquivo de imagem
       |
       v
apps.local.tx -- Pillow -> matriz grayscale
       |
       v
ImageEncoder -> ImageMetadata + bytes codificados
       |
       v
Fragmenter -> Packet -> CRC -> UdpSender
       |
       | UDP localhost, um datagrama por mensagem
       v
UdpReceiver -> Packet.from_bytes -> CRC
       |
       v
Reassembler -> EncodedImage -> ImageDecoder
       |
       v
apps.local.rx -- Pillow -> arquivo e visualizacao
```

## Metadados no pacote

O RX precisa decodificar a imagem sem compartilhar configuracao com o TX.
Por isso, cada pacote transporta:

- Versao do protocolo.
- Tipo de midia.
- Identificador do codec.
- Identificador da imagem.
- Numero e total de fragmentos.
- Largura e altura.
- Quantidade de niveis de grayscale.
- Flags, payload e CRC.

O overhead atual e intencionalmente visivel nos logs. A otimizacao do
cabecalho fica para depois da medicao, conforme o SDD.

## Modos de transmissao MM1 v1

O caminho default continua sendo o modo legado. Cada fragmento possui o
cabecalho v1 de 19 bytes, metadados de imagem, payload e CRC. O primeiro payload
comeca diretamente com dados codificados.

O modo com descritor e uma extensao opt-in implementada no protocolo v1. Ele
mantem o cabecalho, o CRC e os fragmentos posteriores, mas coloca no primeiro
payload um prefixo compacto:

```text
header v1 | marker | descriptor_length | descriptor_body | dados
```

O `Reassembler` atualizado seleciona o modo pela flag `0x04` (todos os
fragmentos), usa o parser puro centralizado e remove o prefixo antes de montar
os dados. O receptor legado nao conhece esse prefixo; portanto os
modos devem ser selecionados explicitamente e nao sao transparentemente
interoperaveis.

```mermaid
flowchart TD
    A[Configuracao explicita] --> B{Modo}
    B -->|Legado| C[Header v1 + dados no primeiro payload]
    B -->|Descritor inline| D[Header v1 + marker + length + descritor + dados]
    C --> E[CRC-16 por pacote]
    D --> E
    E --> F[Transporte substituivel]
    F --> G[Receiver valida pacote]
    G --> H{Descritor presente?}
    H -->|Nao| I[Metadados do cabecalho v1]
    H -->|Sim| J[Reassembler valida e remove prefixo do zero]
    I --> K[Reassembler]
    J --> K
    K --> L[Decoder]
```

O ADR 0004 substitui a proposta anterior de nao duplicar metadata: o corpo v1
repete midia, codec, dimensoes e levels e exige igualdade com os headers.
image_id e contadores nao sao repetidos. O corpo inclui versao e encoded_length
obrigatorio; compressao NONE, parametros extras vazios e nenhum campo FEC.
O limite de payload considera o prefixo de 19 bytes. O RX conserva dados fora de
ordem em armazenamento limitado pelo tamanho derivado de metadata validada,
nao prealoca por comprimentos arbitrarios e so decodifica apos descritor valido,
todos os fragmentos e tamanho exato. Erros estendidos sao terminais; CRC e
validado antes do parser. Legado comeca diretamente com dados, mesmo "TD".

## Interface FEC na arquitetura

FEC nao e parte do encoder de imagem nem do transporte. A camada implementada fica
entre os bytes codificados e a fragmentacao:

```mermaid
flowchart LR
    A[Image Encoder] --> B[Bytes codificados]
    B --> C[Particao em blocos]
    C --> D[FEC Encoder abstrato]
    D --> E[Simbolos de origem e reparo]
    E --> F[FecPacketizer / Fragmenter MM1 v1]
    F --> G[Packet + CRC]
    G --> H[Transport Adapter]
    H --> I[Packet + CRC validado]
    I --> J[FEC Decoder abstrato]
    J --> K[Bytes de origem]
    K --> L[Reassembler e Image Decoder]
```

O contrato abstrato de FEC esta implementado em
`src/meshmedia_lab/fec/contract.py` e documentado em
`docs/error-control.md`. A implementacao standalone de Reed-Solomon em
`src/meshmedia_lab/fec/reed_solomon.py` gera simbolos de reparo em memoria.
`src/meshmedia_lab/fec/transmission.py` prepara blocos sem conhecer o
protocolo; `src/meshmedia_lab/protocol/fec.py` identifica e transporta os
simbolos como uma extensao opt-in dentro do payload MM1 v1.

O modo FEC repete a configuracao, o bloco, o simbolo e os metadados de
comprimento em cada frame. O header MM1 de 19 bytes e o CRC permanecem
inalterados. O RX agrupa frames por transmissao e bloco, trata posicoes ausentes
como erasures e chama o `FecDecoder` antes de entregar os bytes ao decoder de
imagem.

## Execucao

Instale o extra local:

```bash
python3 -m pip install -e '.[local]'
```

Inicie o RX em um terminal:

```bash
PYTHONPATH=src:. python3 -m apps.local.rx --port 9000 --output artifacts/received.png --display --log-level DEBUG
```

Inicie o TX em outro:

```bash
PYTHONPATH=src:. python3 -m apps.local.tx --image input.jpg --port 9000 --resolution 32x32 --levels 16 --payload 64 --log-level DEBUG
```

O teste automatizado equivalente está em
`tests/integration/test_local_apps.py` e inicia TX e RX como processos
separados.

## Fluxo do experimento RGB332

O experimento da Issue #38 pode validar o codec em memoria, pelo caminho MM1
local ou pelo harness UDP localhost. O harness continua separado do protocolo,
enquanto o caminho MM1 usa o pacote v1 sem alterar seu layout:

```text
Imagem RGB ou grayscale
    |
    v
Codec selecionado -> bytes codificados
    |                    |
    |                    +--> contagem analitica de fragmentos MM1
    v                         (payload 64, header 19, CRC 2)
Decoder selecionado -> imagem reconstruida
```

O benchmark e o harness usam Pillow somente na borda para carregar e salvar
imagens. O campo `codec` seleciona grayscale (`0x01`) ou RGB332 (`0x02`) e o
campo `levels` vale `0` somente para RGB332. O Transmission Descriptor nao e
obrigatorio. O harness UDP possui um enquadramento local separado e nao deve
ser confundido com o envelope MM1.

Qt e retransmissao permanecem componentes futuros; o FEC agora e uma extensao
experimental opt-in no pipeline local e o descritor continua opcional.
Pillow e usado pelas aplicacoes locais e pelo benchmark RGB332 somente na
borda. MeshCore continua
sendo um transporte planejado, nao uma capacidade implementada.
Os limites e formatos do transporte MeshCore usados como referencia estao em
[`meshcore-reference.md`](meshcore-reference.md).

## Harness de comparacao da Issue #24

O executor da Issue #24 permanece fora do pacote de protocolo e coordena os
componentes existentes em tres caminhos:

```text
fixture grayscale
    -> encoder
    -> CRC-only: Fragmenter -> Packet -> Reassembler
    -> CRC+RS: FecTransmission -> FecPacketizer -> FecReassembler
    -> RS-only: FecTransmission -> FecSymbolFrame experimental -> RS decoder
```

O simulador de falhas do harness fornece uma sequencia deterministica de
eventos, registra perdas/corrupcoes e aplica corrupcao no payload ou no simbolo.
Ele nao modifica o formato MM1. O RS-only nao passa pelo `Packet` e nao deve ser
interpretado como uma extensao wire do protocolo.

O executor tambem gera as imagens de referencia e resultado, resultados brutos,
resumos, graficos e um visualizador local com dois paineis de mesma escala.


## WebApp browser-only — arquitetura-alvo

A aplicação web é planejada como uma página estática hospedada em GitHub Pages
(HTTPS). O usuário abre a URL e conecta diretamente o MeshCore Companion por
BLE, sem instalar software, clonar o repositório, iniciar backend local ou
executar Docker/Python na máquina.

A WebApp deve consumir o codec Python existente em
src/meshmedia_lab/codec/ **sem alterar ou reescrever sua implementação**.
A hipótese inicial é executá-lo no navegador com Pyodide/WebAssembly. Essa
hipótese precisa ser validada por uma prova de conceito; se não for possível
executar o codec existente sem modificações, a implementação deve parar para
revisão humana, sem criar um codec paralelo.

A biblioteca meshcore.js será avaliada para a conexão Web Bluetooth com o
firmware MeshCore Companion. Sua API real para conexão, notificações e envio de
dados binários de grupo precisa ser confirmada antes de adotá-la. O firmware
Bluetooth atual permanece como caminho primário; USB/Web Serial é alternativa
futura, não requisito.

```mermaid
flowchart LR
    subgraph TX["TX — navegador / HTTPS"]
        TUI["Web UI"] --> PYTX["Pyodide<br/>codec + MM1 existente"]
        PYTX --> BLETX["Adaptador Web Bluetooth"]
    end
    BLETX <--> MESH["MeshCore Companion<br/>canal privado"]
    MESH <--> BLERX["Adaptador Web Bluetooth"]
    subgraph RX["RX — navegador / HTTPS"]
        BLERX --> PYRX["Pyodide<br/>MM1 + codec existente"]
        PYRX --> RUI["Web UI<br/>imagem reconstruída"]
    end
```

GitHub Pages entrega somente os assets estáticos. Upload, preview, codificação,
fragmentação, recepção, reassemblagem e decodificação devem ocorrer no
navegador; imagens e pacotes não são enviados à hospedagem.

A primeira entrega é uma prova de conceito publicada em HTTPS para validar:
suporte Web Bluetooth no navegador/plataforma, seleção e conexão do Companion,
leitura de informações básicas, seleção de canal e troca de uma mensagem de
texto comum. Essa mensagem valida somente a comunicação do Companion; não
transporta bytes MM1. A execução do codec existente no runtime browser fica
para uma etapa posterior e não bloqueia o aceite inicial. Chrome/Edge desktop
são o alvo inicial; suporte Linux deve ser testado cedo. A página deve detectar
ausência de `navigator.bluetooth` e orientar o usuário. Não declarar suporte a
Firefox ou Safari para BLE sem adaptador validado.

O adaptador BLE e as integrações de runtime serão componentes novos, externos
aos módulos de codec existentes. O protocolo MM1 v1 e seus vetores de teste
permanecem inalterados. A integração real continua sujeita a validação com duas
placas físicas e aos limites efetivos do transporte MeshCore.
