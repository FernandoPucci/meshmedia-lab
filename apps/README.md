# Aplicacoes de teste local

A pasta `apps` contem executaveis para validar o protocolo fora dos testes
unitarios. As aplicacoes simulam duas instancias independentes:

```text
apps.local.tx -> UDP localhost -> apps.local.rx
```

O TX carrega uma imagem, usa o codec em `src/meshmedia_lab`, fragmenta os
dados e envia um datagrama UDP por pacote. O RX recebe os datagramas, valida o
CRC, reassembla os fragmentos, usa os metadados recebidos para decodificar e
salva a imagem reconstruida.

## Por que esta pasta existe

O pacote em `src/meshmedia_lab` e o nucleo portavel do laboratorio. Ele nao
depende de Pillow, GUI ou MeshCore.

As aplicacoes em `apps/local` simulam o ambiente externo ao nucleo:

- Leitura de arquivos de imagem.
- Conversao para grayscale.
- Comunicacao entre processos.
- Logs do trafego.
- Visualizacao da imagem reconstruida.
- Medicao de mensagens e overhead.

Essa separacao permite trocar UDP por um adaptador MeshCore no futuro sem
alterar o encoder ou o decoder.

## Estrutura

```text
apps/
├── README.md
└── local/
    ├── __init__.py
    ├── common.py       # Parser de resolucao, logs e contadores
    ├── image_io.py     # Integracao Pillow
    ├── rx.py           # Processo receptor
    ├── tx.py           # Processo transmissor
    ├── rgb332_rx.py    # RX UDP experimental separado do MM1
    └── rgb332_tx.py    # TX UDP experimental separado do MM1
```

O transporte UDP reutilizavel fica no nucleo em
`src/meshmedia_lab/transport/udp.py`. As aplicacoes apenas coordenam o
transporte e os componentes do protocolo.

## Instalacao

Na raiz do repositorio, instale o extra das aplicacoes locais:

```bash
python3 -m pip install -e '.[local]'
```

Para instalar tambem as ferramentas e testes de desenvolvimento:

```bash
python3 -m pip install -e '.[local,dev]'
```

O extra `local` instala Pillow. O nucleo continua sem dependencia obrigatoria
de imagem.

## Execucao basica

Os comandos devem ser executados na raiz do repositorio. Inicie o RX primeiro
para que ele esteja escutando antes do envio.

### Terminal 1: receptor

```bash
PYTHONPATH=src:. python3 -m apps.local.rx \
  --bind 127.0.0.1 \
  --port 9000 \
  --output artifacts/received.png \
  --display \
  --log-level DEBUG
```

O receptor permanece ativo ate completar uma imagem ou atingir o timeout. O
arquivo sempre e salvo em `--output`. A opcao `--display` abre o visualizador
de imagens do sistema usando Pillow.

### Terminal 2: transmissor

```bash
PYTHONPATH=src:. python3 -m apps.local.tx \
  --image caminho/para/imagem.jpg \
  --host 127.0.0.1 \
  --port 9000 \
  --resolution 32x32 \
  --levels 16 \
  --payload 64 \
  --image-id 1 \
  --log-level DEBUG
```

O TX usa a imagem original como entrada, converte para grayscale e deixa o
`ImageEncoder` fazer o redimensionamento para `--resolution`.

O par `rgb332_tx`/`rgb332_rx` usa um enquadramento experimental separado do
MM1. Para testar o caminho MM1 com selecao de codec, use `apps.local.tx` e
`apps.local.rx` com `--codec grayscale` ou `--codec rgb332`.

Exemplo RGB332 no caminho MM1:

```bash
PYTHONPATH=src:. python3 -m apps.local.tx \
  --image caminho/para/imagem.jpg \
  --port 9000 \
  --resolution 32x32 \
  --codec rgb332 \
  --payload 64 \
  --image-id 38
```

O RX seleciona o decoder pelo metadata recebido. `--codec` permanece uma
opcao do TX; o default e `grayscale`.

### Descritor inline opcional

Adicione `--transmission-mode descriptor` ao TX para transmitir o contrato
explicito de codec e parametros no primeiro payload. O RX atualizado aceita
ambos os modos pela flag `0x04`, sem opcoes compartilhadas nem heuristicas.
O header MM1 e o CRC nao mudam. O prefixo custa 19 bytes; com payload 64,
RGB332 `32x32` passa de 16 a 17 mensagens, `64x64` de 64 a 65.

O limite de payload deve ser pelo menos 19. Exatamente 19 permite fragmento
zero somente com descritor. Dados finais devem ter o comprimento declarado
exato. Erros do descritor sao terminais (exit 1, sem salvar imagem), inclusive
com `--keep-listening`; um novo ensaio usa um novo RX. Timeout permanece de
inatividade. Nao enviar esse modo a receptores legados. O default `legacy`
mantem os bytes anteriores, mesmo quando os dados comecam por "TD".

Contrato: [`docs/transmission-descriptor.md`](../docs/transmission-descriptor.md).

## Opcoes do TX

| Opcao | Padrao | Descricao |
|---|---:|---|
| `--image` | obrigatorio | Caminho da imagem de entrada. |
| `--host` | `127.0.0.1` | Endereco do RX. |
| `--port` | `9000` | Porta UDP do RX. |
| `--resolution` | `32x32` | Resolucao alvo no formato `LARGURAxALTURA`. |
| `--codec` | `grayscale` | `grayscale` ou `rgb332`. |
| `--levels` | `16` | Quantidade de tons de grayscale. |
| `--payload` | `64` | Bytes de payload por pacote. |
| `--image-id` | `1` | Identificador da transmissao. |
| `--transmission-mode` | `legacy` | `legacy` ou `descriptor` (RX atualizado). |
| `--log-level` | `INFO` | Nivel `DEBUG`, `INFO`, `WARNING` ou `ERROR`. |
| `--log-file` | vazio | Arquivo opcional para os logs. |

Os niveis aceitos atualmente sao `2`, `4`, `8`, `16` e `256`. O parametro
`--levels` se aplica somente ao grayscale; RGB332 usa canais fixos `3/3/2`.

## Opcoes do RX

| Opcao | Padrao | Descricao |
|---|---:|---|
| `--bind` | `127.0.0.1` | Endereco local para escutar. |
| `--port` | `9000` | Porta UDP local. |
| `--output` | `received.png` | Arquivo da imagem reconstruida. |
| `--display` | desativado | Abre o visualizador do sistema. |
| `--timeout` | `30` | Segundos sem pacote antes de sair. |
| `--keep-listening` | desativado | Continua esperando outras imagens. |
| `--log-level` | `INFO` | Nivel de log. |
| `--log-file` | vazio | Arquivo opcional para os logs. |

## Fluxo de dados

```text
Arquivo de imagem
       |
       v
Pillow: abertura e grayscale
       |
       v
ImageEncoder: resize, quantizacao e empacotamento
       |
       v
Fragmenter: divisao em mensagens
       |
       v
Packet: metadados, payload e CRC
       |
       v
UdpSender === UDP localhost ===> UdpReceiver
                                      |
                                      v
                              Packet.from_bytes
                                      |
                                      v
                                Reassembler
                                      |
                                      v
                                  Decoder
                                      |
                                      v
                         arquivo e visualizacao
```

## Metadados transportados

Cada pacote carrega os metadados necessarios para o RX trabalhar sem repetir
as opcoes do TX:

- Versao do protocolo.
- Tipo de midia.
- Identificador do codec.
- Identificador da imagem.
- Numero do fragmento.
- Total de fragmentos.
- Largura e altura.
- Niveis de grayscale.
- Flags de primeiro e ultimo fragmento.
- Tamanho e bytes do payload.
- CRC-16/CCITT-FALSE.

O cabecalho atual possui overhead intencional. O objetivo desta etapa e medir
esse custo antes de otimizar o formato para o MeshCore.

## Logs e contador de mensagens

Com `--log-level DEBUG`, cada pacote mostra os bytes reais enviados ou
recebidos:

```text
TX msg=3/8 message_bytes=85
  image_id=1
  flags=0x00
  resolution=32x32
  levels=16
  payload_bytes=64
  overhead_bytes=21
  address=127.0.0.1:9000
  raw:
    4d 4d 01 01 01 00 00 01 00 02 00 08 00 20 00 20
    00 10 40 ...
RX msg=3/8 message_bytes=85
  image_id=1
  flags=0x00
  resolution=32x32
  levels=16
  payload_bytes=64
  overhead_bytes=21
  address=127.0.0.1:58533
  raw:
    4d 4d 01 01 01 00 00 01 00 02 00 08 00 20 00 20
    00 10 40 ...
RX summary
  messages=8
  payload_bytes=512
  message_bytes_total=680
  overhead_bytes=168
  invalid_packets=0
  expected_messages=8
```

O valor `3/8` significa que o pacote atual e o terceiro de oito. O contador
principal da imagem e `Total Fragments`. O resumo separa bytes de cabecalho/CRC
(`overhead_bytes`) e informa `descriptor_bytes` (zero no legado; 19 por
fragmento zero recebido no modo descriptor). `payload_bytes` inclui o descritor;
subtraia `descriptor_bytes` para obter bytes de imagem nesses datagramas.

Para guardar os logs:

```bash
PYTHONPATH=src:. python3 -m apps.local.rx \
  --port 9000 \
  --output artifacts/received.png \
  --log-level DEBUG \
  --log-file artifacts/rx.log
```

Em outro terminal:

```bash
PYTHONPATH=src:. python3 -m apps.local.tx \
  --image input.png \
  --port 9000 \
  --resolution 64x64 \
  --payload 20 \
  --log-level DEBUG \
  --log-file artifacts/tx.log
```

## Teste automatizado

O teste `tests/integration/test_local_apps.py` inicia TX e RX como processos
separados, cria uma imagem temporaria, transmite por uma porta UDP local e
verifica o arquivo reconstruido.

```bash
PYTHONPATH=src:. python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Esse teste valida o mesmo caminho usado manualmente, sem depender de um
visualizador grafico.

## Limitacoes atuais

- UDP local nao simula automaticamente perda, latencia ou jitter de radio.
- Nao existe ACK, NACK ou retransmissao.
- FEC e Reed-Solomon estao implementados como extensao opt-in experimental no
  pipeline local. O modo RS-only da Issue #24 existe somente no harness de
  benchmarks e nao altera o MM1 v1.
- RLE, JPEG baseline e transmissao progressiva ainda nao estao integrados.
- O visualizador depende de um ambiente grafico; `--output` continua disponivel
  em ambientes headless.
- A integracao com MeshCore sera feita por outro `TransportAdapter` depois da
  validacao deste fluxo.
