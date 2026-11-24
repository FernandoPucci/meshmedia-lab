# Referencias tecnicas

Esta bibliografia separa artigos academicos, documentos normativos e catalogos
de implementacao. As referencias sao utilizadas para justificar conceitos e
parametros; elas nao substituem os testes do repositorio.

## RS60

Reed, I. S.; Solomon, G. (1960). *Polynomial Codes Over Certain Finite
Fields*. Journal of the Society for Industrial and Applied Mathematics, 8(2),
300-304. [DOI: 10.1137/0108018](https://doi.org/10.1137/0108018).

Tipo: artigo original. Uso: origem dos codigos Reed-Solomon e dos codigos de
bloco sobre campos finitos.

## RFC5510

Lacan, J.; Roca, V.; Peltotalo, J.; Peltotalo, S. (2009). *Reed-Solomon
Forward Error Correction (FEC) Schemes*. RFC 5510. [RFC Editor](https://www.rfc-editor.org/rfc/rfc5510).

Tipo: documento normativo IETF, Standards Track. Uso: terminologia de source
symbols, repair symbols, code rate, blocos de origem e canais de erasure; tambem
apresenta esquemas RS sobre `GF(2^m)` para transporte orientado a pacotes.

## HAMMING50

Hamming, R. W. (1950). *Error Detecting and Error Correcting Codes*. Bell
System Technical Journal, 29(2), 147-160. [DOI:
10.1002/j.1538-7305.1950.tb00463.x](https://doi.org/10.1002/j.1538-7305.1950.tb00463.x).

Tipo: artigo academico. Uso: fundamentos de deteccao e correcao de erros.

## SHANNON48

Shannon, C. E. (1948). *A Mathematical Theory of Communication*. Bell System
Technical Journal, 27(3), 379-423. [DOI:
10.1002/j.1538-7305.1948.tb01338.x](https://doi.org/10.1002/j.1538-7305.1948.tb01338.x).

Tipo: artigo academico fundador da teoria da informacao. Uso: contexto para
redundancia, capacidade de canal e limites de comunicacao.

## KOOPMAN2004

Koopman, P.; Chakravarty, T. (2004). *Cyclic Redundancy Code (CRC) Polynomial
Selection for Embedded Networks*. International Conference on Dependable
Systems and Networks, 145-154. [DOI:
10.1109/DSN.2004.1311885](https://doi.org/10.1109/DSN.2004.1311885).

Tipo: artigo de conferencia. Uso: avaliacao da capacidade de polinomios CRC em
redes embarcadas e cautela contra a escolha baseada apenas no nome do CRC.

## V41

ITU-T. *Recommendation V.41: Code-independent error-control system*.
[Pagina oficial da recomendacao](https://www.itu.int/rec/T-REC-V.41/en).

Tipo: recomendacao normativa. Uso: referencia para o sistema de controle de
erros associado a variantes historicas do polinomio `0x1021`.

## CRC-CATALOGUE

Cook, G. *Catalogue of parametrised CRC algorithms*, CRC RevEng. [Catalogo de
CRCs de 16 bits](https://reveng.sourceforge.io/crc-catalogue/16.htm).

Tipo: catalogo tecnico de parametrizacao e vetores de validacao; nao e uma
publicacao academica. Uso: confirmar a tupla `width`, `poly`, `init`, `refin`,
`refout`, `xorout`, `check` e `residue` do CRC-16/CCITT-FALSE, tambem listado
como CRC-16/IBM-3740.

## LORA2016

Augustin, A.; Yi, J.; Clausen, T.; Townsley, W. (2016). *A Study of LoRa:
Long Range & Low Power Networks for the Internet of Things*. Sensors, 16(9),
1466. [DOI: 10.3390/s16091466](https://doi.org/10.3390/s16091466).

Tipo: artigo academico. Uso: contexto de redes LoRa, limitacoes de taxa,
alcance, energia e custo de transmissao. Nao e uma especificacao do MeshCore.

## MESHCORE-PACKET

MeshCore developers. *Packet Format*. Documentacao oficial do protocolo nivel
1. [MeshCore `docs/packet_format.md`](https://github.com/meshcore-dev/MeshCore/blob/main/docs/packet_format.md).

Tipo: documentacao oficial de implementacao. Uso: estrutura do pacote, header,
tipos de rota, tipos de payload, path, limites de 184 bytes de payload e
`MAX_TRANS_UNIT`.

## MESHCORE-PAYLOADS

MeshCore developers. *Payload Format*. [MeshCore
`docs/payloads.md`](https://github.com/meshcore-dev/MeshCore/blob/main/docs/payloads.md).

Tipo: documentacao oficial de implementacao. Uso: campos internos de
`GRP_DATA`, `RAW_CUSTOM`, anuncios, ACKs, mensagens e datagramas.

## MESHCORE-SOURCE

MeshCore developers. *MeshCore source definitions*. [MeshCore
`src/MeshCore.h`](https://github.com/meshcore-dev/MeshCore/blob/main/src/MeshCore.h),
[`src/Packet.h`](https://github.com/meshcore-dev/MeshCore/blob/main/src/Packet.h)
e [`src/Packet.cpp`](https://github.com/meshcore-dev/MeshCore/blob/main/src/Packet.cpp).

Tipo: fonte oficial. Uso: confirmar `MAX_PACKET_PAYLOAD`, `MAX_PATH_SIZE`,
`MAX_TRANS_UNIT`, codificacao de `path_length` e calculo do tamanho bruto.

## MESHCORE-KISS

MeshCore developers. *MeshCore KISS Modem Protocol*. [Documentacao oficial
KISS](https://github.com/meshcore-dev/MeshCore/blob/main/docs/kiss_modem_protocol.md).

Tipo: documentacao oficial de interface. Uso: limite de 255 bytes para o pacote
raw, enquadramento serial e comando `GetAirtime` (`0x0F`).

## MESHCORE-RADIO-PRESETS

MeshCore developers. *Radio Presets*. [Documentacao oficial de
presets](https://github.com/meshcore-dev/MeshCore/blob/main/docs/radio_presets.md).

Tipo: documentacao operacional. Uso: mostrar que frequencia, bandwidth,
spreading factor e coding rate sao configuracoes dependentes da regiao e nao
uma constante universal do MM1.

## Politica de referencias

Uma afirmacao matematica ou de funcionamento de um algoritmo deve apontar para
uma fonte primaria, um padrao ou uma fonte tecnica identificada. Textos de
blog, respostas de forum e a conversa compartilhada podem ajudar na exploracao,
mas nao sao usados como referencia normativa do repositorio.

Links DOI e paginas oficiais devem ser preservados quando uma referencia for
atualizada. O catalogo CRC deve ser tratado como fonte de parametrizacao, nao
como prova academica da eficacia de uma configuracao.
