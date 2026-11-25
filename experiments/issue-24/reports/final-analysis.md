# Issue #24 — análise final

> Resultado de 9.450 execuções em simulação local determinística.
> Não representa rádio MeshCore, LoRa, airtime ou latência real.

## Resumo quantitativo

| Estratégia | Sucesso degradado | Overhead sem falhas | Tempo total sem falhas |
|---|---:|---:|---:|
| CRC+RS(32,20) | 75.56% | 10861.46% | 7637.23 ms |
| CRC+RS(32,24) | 51.43% | 9090.62% | 6235.52 ms |
| CRC+RS(32,28) | 25.40% | 7806.77% | 5293.99 ms |
| CRC-only | 22.30% | 32.81% | 196.09 ms |
| RS-only(32,20) | 45.24% | 7476.30% | 2098.16 ms |
| RS-only(32,24) | 32.94% | 6252.34% | 1978.36 ms |
| RS-only(32,28) | 16.11% | 5364.97% | 1609.38 ms |

## Respostas

1. **Menor overhead:** CRC-only no caminho MM1 legado, com 32.81% no cenário sem falhas. O RS-only possui enquadramento diferente e não inclui header/CRC MM1.

2. **Maior recuperação média:** CRC+RS(32,20), com 75.56% nos cenários degradados.

3. **Mais reparos:** no CRC+RS, a recuperação degradada aumentou de 25.40% para 75.56% ao passar de 4 para 12 reparos, ao custo de mais mensagens e overhead.

4. **Tamanho da imagem:** o grayscale 16 níveis produz 512, 2.048 e 8.192 bytes em 32x32, 64x64 e 128x128. O número de mensagens e blocos cresce proporcionalmente; a distribuição por bloco passa a dominar a recuperação.

5. **CRC-only:** não recupera perdas. Pacotes corrompidos são rejeitados e a imagem fica incompleta quando falta qualquer fragmento necessário.

6. **CRC+RS:** recuperou integralmente as células em que as erasures por bloco permaneceram dentro da capacidade RS. RS(32,20) foi a configuração mais tolerante, mas também a mais cara.

7. **RS-only:** produziu 126 saídas divergentes e 5305 execuções sem saída entre as variantes. Uma saída do decoder não deve ser tratada como integridade validada.

8. **Custo computacional:** Reed-Solomon aumentou o tempo local de preparação/decodificação em relação ao CRC-only. Esses tempos são do Python e não representam airtime.

9. **Vantagem CRC+RS:** o CRC identifica corrupção antes da reassemblagem e transforma o pacote inválido em erasure; o RS usa essa informação para recuperar o bloco sem aceitar silenciosamente dados corrompidos.

10. **Limitações:** payload fixo de 64 bytes, um símbolo FEC por mensagem, canal independente por pacote, sem rajadas/jitter, sem MeshCore real e sem medição de airtime. O RS-only continua exclusivamente experimental.

Os detalhes por fixture, resolução, cenário, repetição e seed estão em `results/raw/` e `results/summary/`.
