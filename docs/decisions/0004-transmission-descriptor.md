# ADR 0004 — Transmission Descriptor inline v1

- Data: 2026-11-24
- Estado: contrato aprovado para implementacao nesta branch; sujeito a revisao da PR
- Rastreabilidade: Issues #17, #18 e #5

## Contexto e autorizacao

A Etapa A propunha um prefixo sem duplicar metadados do cabecalho e ainda sem
marcador/corpo definidos. A ordem de trabalho posterior a PR #42 pediu um
descritor autodescritivo. A proposta foi apresentada na conversa de revisao;
o mantenedor solicitou criar uma branch apartada e executar a implementacao.

## Decisao

- Registrar `INLINE_DESCRIPTOR=0x04` no campo flags existente, em todos os
  fragmentos estendidos. Nao alterar FIRST/LAST, offsets, header de 19 bytes
  ou CRC-16/CCITT-FALSE.
- Usar `54 44` ("TD"), comprimento uint8 e corpo v1 de 16 bytes big-endian.
- Repetir media_type, codec, dimensoes e levels no descritor; exigir igualdade
  com todos os cabecalhos. Nao repetir identificador ou contadores.
- Comprimento codificado obrigatorio uint32, validado contra codec/dimensoes
  e contra a soma final de dados. Parametros adicionais vazios, compressao NONE.
- Legado continua default. RX seleciona modo pela flag, nunca por heuristica
  de magic ou tamanho. Nao ha negociacao automatica nem fallback de erro.
- Prefixo inteiro no fragmento zero. Rejeitar payload limite menor que 19;
  exatamente 19 permite fragmento inicial so com descritor.
- Sem FEC, TLV, campos repetidos, compressao ou algoritmos adicionais neste corpo.
  Outros parametros exigem nova revisao do descritor e revisao humana.

## Alternativas e custos

Reconhecer apenas "TD" colide com dados legados arbitrarios. Selecao externa
sem flag exige configuracao RX compartilhada. TLV e mascara de presenca foram
adiados para manter o contrato inicial estrito. Um corpo sem duplicacao e menor,
mas nao atende a nova exigencia de autodescricao.

O prefixo custa 19 bytes por transmissao e pode acrescentar um pacote.
Receptores legados nao sao compativeis com o modo estendido: alguns ignoram
flags desconhecidas e tentarao decodificar o prefixo. Enviar somente quando o
suporte do RX for conhecido. Os bytes do modo legado permanecem inalterados.

O contrato completo e seus vetores estao em `docs/transmission-descriptor.md`.
O estado de codigo/testes e registrado separadamente na matriz de implementacao.
