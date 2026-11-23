# MeshMedia Lab

Laboratorio experimental de codecs e protocolos para transmissao de imagens e
audio sobre redes MeshCore/LoRa.

O projeto segue o documento de Specification-Driven Development em
[`sdd/sdd.md`](sdd/sdd.md).

## Estrutura

```text
.
├── docs/                    # Decisoes e arquitetura do laboratorio
├── sdd/                     # Especificacao orientadora do projeto
├── src/meshmedia_lab/
│   ├── application/         # Casos de uso e pipeline
│   ├── codec/               # Encoder e decoder de imagem
│   ├── protocol/            # Pacotes, CRC, fragmentacao e reassemblagem
│   ├── simulation/          # Simulacao de canal
│   └── transport/           # Adaptadores, transmissor e receptor
├── tests/
│   ├── integration/         # Testes do pipeline completo
│   └── unit/                # Testes isolados por componente
├── benchmarks/              # Experimentos de desempenho
└── pyproject.toml
```

## Desenvolvimento

O projeto nao depende de bibliotecas de imagem ou de radio na primeira fase.
Isso permite validar o pipeline localmente antes da integracao com MeshCore.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Com as dependencias de desenvolvimento instaladas, os mesmos testes podem ser
executados com `pytest`.

## Testes locais

O projeto ainda nao possui CLI nem interface grafica. Os cenarios abaixo usam
diretamente a API Python e devem ser executados na raiz do repositorio.

### Smoke test end-to-end

Este fluxo testa:

```text
Imagem -> Encoder -> Fragmenter -> Pacotes -> Receiver
       -> Reassembler -> Decoder -> Imagem reconstruida
```

```bash
PYTHONPATH=src python3 - <<'PY'
from meshmedia_lab.application.pipeline import ImagePipeline
from meshmedia_lab.protocol.fragmenter import Fragmenter

image = tuple(
    tuple((x * 32 + y * 16) % 256 for x in range(8))
    for y in range(8)
)

pipeline = ImagePipeline(
    fragmenter=Fragmenter(max_payload_size=16)
)

result = pipeline.transmit(image, image_id=123)

print("Bytes codificados:", result.encoded_size)
print("Pacotes enviados:", result.packets_sent)
print("Pacotes recebidos:", result.packets_received)
print("Dimensao reconstruida:", len(result.image), "x", len(result.image[0]))
PY
```

### Teste de perda de pacotes

```bash
PYTHONPATH=src python3 - <<'PY'
from meshmedia_lab.application.pipeline import ImagePipeline, TransmissionError
from meshmedia_lab.protocol.fragmenter import Fragmenter
from meshmedia_lab.simulation.channel import ChannelConfig, ChannelSimulator

image = ((0, 128), (255, 64))

pipeline = ImagePipeline(
    fragmenter=Fragmenter(max_payload_size=1)
)

channel = ChannelSimulator(
    ChannelConfig(loss_rate=1.0, seed=42)
)

try:
    pipeline.transmit(image, image_id=1, channel=channel)
except TransmissionError as error:
    print("Falha esperada:", error)
PY
```

### Teste de corrupcao

```bash
PYTHONPATH=src python3 - <<'PY'
from meshmedia_lab.application.pipeline import ImagePipeline, TransmissionError
from meshmedia_lab.protocol.fragmenter import Fragmenter
from meshmedia_lab.simulation.channel import ChannelConfig, ChannelSimulator

image = ((0, 128), (255, 64))

pipeline = ImagePipeline(
    fragmenter=Fragmenter(max_payload_size=1)
)

channel = ChannelSimulator(
    ChannelConfig(corruption_rate=1.0, seed=42)
)

try:
    pipeline.transmit(image, image_id=1, channel=channel)
except TransmissionError as error:
    print("Corrupcao detectada:", error)
PY
```

### Teste do transporte em memoria

Este cenario testa o adaptador de transporte, o transmissor, o receptor e a
reassemblagem fora de ordem.

```bash
PYTHONPATH=src python3 - <<'PY'
from meshmedia_lab.protocol import Fragmenter, Reassembler
from meshmedia_lab.transport import InMemoryTransport, Receiver, Transmitter

packets = Fragmenter(max_payload_size=3).fragment(
    b"abcdefgh",
    image_id=7,
)

transport = InMemoryTransport()
sent = Transmitter(transport).transmit(packets)
raw_packets = transport.drain()

receiver = Receiver()
reassembler = Reassembler()

for raw_packet in reversed(raw_packets):
    reassembler.add(receiver.receive(raw_packet))

print("Pacotes enviados:", sent)
print("Completo:", reassembler.is_complete)
print("Dados:", reassembler.assemble())
PY
```

## Limitacoes atuais

- Nao e possivel carregar JPEG ou PNG diretamente.
- A imagem e fornecida como matriz de pixels.
- Nao ha visualizacao grafica.
- Nao ha comunicacao real com MeshCore.
- FEC, retransmissao e RLE ainda nao estao implementados.
- O pipeline ainda usa o transporte em memoria diretamente.
