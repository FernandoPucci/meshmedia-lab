# Ordem de trabalho para o OpenCode — Etapa C: contrato abstrato de FEC

- **Projeto:** MeshMedia Lab
- **Etapa:** C — controle de erros parametrizável
- **Issue principal:** [#19 — Implementar contrato abstrato da interface FEC](https://github.com/FernandoPucci/meshmedia-lab/issues/19)
- **Branch-base:** `master`
- **Tipo desta atividade:** implementação de contrato e testes; não implementar algoritmo FEC
- **Abordagem:** Specification-Driven Development (SDD)
- **Estado:** instrução de execução; não representa funcionalidade já implementada

Este documento orienta o OpenCode a executar somente a primeira atividade da Etapa C: transformar o contrato lógico de FEC documentado em uma API Python abstrata, validável e testável, independente de Reed-Solomon ou de qualquer outro algoritmo concreto.

O documento complementa, mas não substitui, `AGENTS.md`, `docs/OPENCODE-WORK-ORDER.md`, `sdd/sdd.md` e `docs/error-control.md`. Em caso de divergência, interrompa a implementação e apresente a divergência para revisão humana.

---

## 1. Objetivo exato

Implementar uma camada abstrata de Forward Error Correction (FEC) que:

1. defina uma configuração explícita e validável;
2. defina a representação dos símbolos e blocos;
3. defina operações abstratas de codificação e decodificação;
4. defina resultados de sucesso e falha de decodificação;
5. estabeleça comportamento consistente para entradas inválidas, duplicatas, índices, comprimentos, erasures e blocos incompletos;
6. permita testar o contrato sem depender de Reed-Solomon;
7. mantenha FEC independente do protocolo MM1, dos codecs de imagem e dos transportes.

**Não implementar Reed-Solomon nesta atividade.** A conclusão da Issue #19 significa que existe um contrato abstrato testado; não significa que o projeto já consegue recuperar dados com FEC.

## 2. Leitura obrigatória antes de alterar código

Na branch de trabalho, leia integralmente e considere a versão atual dos seguintes arquivos:

1. `AGENTS.md`;
2. `README.md`;
3. `sdd/sdd.md`;
4. `docs/OPENCODE-WORK-ORDER.md`;
5. `docs/implementation-status.md`;
6. `docs/architecture.md`;
7. `docs/error-control.md`;
8. `docs/experiment-matrix.md`;
9. `pyproject.toml`;
10. módulos e testes atuais de protocolo, codec, pipeline e transporte.

Inspecione também a estrutura real de `src/meshmedia_lab/` e `tests/`. Não presuma que diretórios ou APIs mencionados nesta ordem já existam.

A Issue #19 estabelece o seguinte critério de aceite:

> Contrato testável e independente de um algoritmo específico; erros e limites têm comportamento definido.

A seção 4.1 de `docs/error-control.md` é a referência conceitual inicial para as operações e os campos da configuração.

## 3. Limites obrigatórios de escopo

### Dentro do escopo

- configuração abstrata de FEC;
- tipos de dados para símbolos, bloco codificado e resultado de decodificação;
- interfaces abstratas de encoder e decoder;
- validação de parâmetros genéricos;
- semântica de índices e erasures;
- políticas explícitas para padding e blocos incompletos;
- exceções e resultados de erro com comportamento documentado;
- testes unitários do contrato usando uma implementação falsa/de teste;
- documentação e rastreabilidade da implementação.

### Fora do escopo — não implementar

- Reed-Solomon, Hamming, BCH, LDPC ou qualquer algoritmo real;
- dependência de biblioteca externa de FEC;
- integração FEC ao `ImagePipeline`;
- integração ao `Fragmenter`, `Reassembler`, `Packet` ou `TransmissionDescriptor`;
- geração ou transporte de símbolos de reparo em pacotes MM1;
- campos FEC no cabeçalho ou no descritor;
- flag FEC nas flags MM1;
- alteração do CRC-16/CCITT-FALSE;
- ACK, NACK ou retransmissão;
- integração MeshCore/LoRa;
- framework geral de benchmarks;
- mudança do wire format MM1 v1.

Se a implementação do contrato parecer exigir qualquer alteração nesses componentes, pare e apresente a necessidade e as alternativas. Não faça a alteração por conveniência.

## 4. Princípios arquiteturais

### 4.1 FEC não pertence ao protocolo de pacotes

A camada FEC deve operar sobre blocos de bytes/símbolos produzidos antes da fragmentação MM1. Ela não deve conhecer:

- cabeçalho MM1;
- CRC de pacote;
- `image_id`;
- números de fragmentos MM1;
- flags do pacote;
- UDP;
- MeshCore;
- codecs grayscale ou RGB332.

O contrato deve ser reutilizável por diferentes algoritmos e transportes.

A arquitetura lógica de referência continua sendo:

```text
bytes codificados pelo codec
  -> particionamento em blocos FEC
  -> encoder FEC
  -> símbolos de origem + símbolos de reparo
  -> fragmentação MM1 (futuro, fora desta issue)
  -> CRC por pacote
  -> transporte
```

No sentido inverso, uma futura integração fará a validação do pacote/CRC antes de entregar símbolos válidos ou erasures ao decoder FEC.

### 4.2 CRC continua independente

O CRC-16/CCITT-FALSE já implementado continua responsável por detectar corrupção no pacote. FEC é uma camada adicional que poderá recuperar dados ausentes ou identificados como inválidos.

Não remover, substituir ou alterar a função do CRC. Não tratar CRC e FEC como sinônimos.

### 4.3 Não acoplar a interface a Reed-Solomon

A interface não deve exigir propriedades exclusivas de RS, como campo finito específico, polinômio gerador ou implementação em GF(2^8).

Parâmetros como `k`, `r` e `n` podem fazer parte da configuração genérica conforme o contrato já documentado, mas validações algorítmicas específicas devem pertencer à implementação concreta futura.

## 5. Contrato lógico a materializar

Os nomes abaixo são os nomes conceituais já registrados em `docs/error-control.md`. O OpenCode deve inspecionar as convenções do código atual e pode ajustar detalhes idiomáticos de Python, desde que preserve a semântica e documente qualquer alteração.

### 5.1 Configuração: `FecConfig`

A configuração deve representar explicitamente, no mínimo:

| Campo | Significado | Regra mínima |
|---|---|---|
| `algorithm_id` | Identificador estável do algoritmo | String não vazia; não presumir algoritmo implementado |
| `symbol_size` | Tamanho de cada símbolo em bytes | Inteiro positivo |
| `data_symbols` (`k`) | Quantidade de símbolos de origem | Inteiro positivo |
| `repair_symbols` (`r`) | Quantidade de símbolos de reparo | Inteiro não negativo |
| `block_symbols` (`n`) | Quantidade total de símbolos do bloco | Inteiro positivo; validar relação com k+r conforme o contrato |
| `interleaving_depth` | Profundidade de intercalação | Inteiro não negativo; zero significa sem intercalação |
| `padding_policy` | Política de preenchimento do bloco final | Valor explícito e validado |
| `incomplete_block_policy` | Política para bloco com menos de k símbolos de origem | Valor explícito e validado |

Requisitos:

- A configuração deve ser imutável após a criação, preferencialmente seguindo o padrão de dataclasses imutáveis já utilizado no projeto.
- Rejeitar tipos e valores inválidos com erro claro e previsível.
- Não aceitar booleanos como inteiros apenas porque `bool` herda de `int` em Python.
- Não permitir valores negativos para tamanhos, quantidades ou profundidade.
- Validar `n = k + r` no contrato genérico se essa relação for adotada como invariável. Se houver motivo para permitir exceção, documentar e testar a regra antes de implementá-la.
- Não inventar limites máximos sem necessidade demonstrada. Se houver limite técnico necessário, justificar e documentar.
- Não incluir parâmetros específicos de Reed-Solomon na configuração abstrata.
- Não adicionar presets ou perfis nomeados.

As políticas de padding e de bloco incompleto precisam ser representadas por tipos/valores explícitos, e não por strings livres espalhadas pelo código. O OpenCode deve definir um conjunto pequeno e documentado de opções coerente com `docs/error-control.md`.

A especificação atual apresenta como alternativas para o bloco final: rejeitar, preencher até k símbolos ou usar representação explícita de comprimento. Não escolha silenciosamente uma semântica diferente. Para esta etapa, formalize a política escolhida no contrato e registre as alternativas não adotadas como decisões futuras, sem introduzir formato de rede.

### 5.2 Símbolos e índices

A API deve representar símbolos com:

- índice inteiro;
- conteúdo em bytes;
- tamanho coerente com `symbol_size`.

Os índices devem ser inequívocos:

- símbolos de origem: intervalo `0 .. k-1`;
- símbolos de reparo: intervalo `k .. n-1`.

O contrato deve deixar claro se os símbolos são representados por uma classe própria ou por uma estrutura equivalente. Evite tuplas posicionais ambíguas e evite misturar índice de símbolo com número de fragmento MM1.

Validar:

- índice negativo;
- índice fora de `0 .. n-1`;
- conteúdo vazio quando não permitido;
- comprimento diferente de `symbol_size`;
- índice duplicado no conjunto recebido;
- símbolo de origem e de reparo sem distinção clara.

### 5.3 Resultado de codificação: `EncodedBlock`

O contrato lógico de codificação é:

```text
FecEncoder.encode(source_block, config)
    -> EncodedBlock(source_symbols, repair_symbols, metadata)
```

O resultado deve distinguir claramente:

- símbolos de origem, com índices `0 .. k-1`;
- símbolos de reparo, com índices `k .. n-1`;
- quantidade de bytes originais;
- quantidade de bytes de padding;
- metadados locais necessários para reconstruir o bloco original.

O resultado deve permitir verificar que:

- a quantidade de símbolos de origem respeita a configuração;
- a quantidade de símbolos de reparo respeita a configuração;
- todos os símbolos têm tamanho fixo;
- os índices são únicos e ocupam os intervalos definidos;
- o comprimento original e o padding são coerentes.

O encoder recebe bytes de origem e configuração. Não serializa pacotes, não calcula CRC e não acessa transporte.

### 5.4 Resultado de decodificação: `DecodeResult`

O contrato lógico é:

```text
FecDecoder.decode(received_symbols, erasures, config)
    -> DecodeResult(
        source_block,
        recovered_symbols,
        success,
        reason
    )
```

O resultado deve informar, no mínimo:

- sucesso ou falha;
- bytes de origem recuperados, sem padding quando a recuperação for bem-sucedida;
- quantidade de símbolos recuperados;
- índices dos símbolos recuperados;
- índices ausentes ou inválidos relevantes;
- motivo padronizado da falha.

Defina uma representação consistente para o motivo de falha. Não dependa de mensagens livres de exceção para que consumidores descubram a categoria do erro.

Distinga dois tipos de situação:

1. **Entrada inválida para a API:** configuração incompatível, índice fora dos limites, duplicata, símbolo com tamanho errado ou inconsistência estrutural. Deve gerar exceção específica da camada FEC.
2. **Decodificação válida, mas sem dados suficientes para recuperar o bloco:** deve retornar um resultado de falha com motivo explícito, sem fingir que houve recuperação.

O contrato deve definir se uma falha de decodificação retorna `source_block=None` e garantir que dados parciais não sejam apresentados como bloco completo.

### 5.5 Erasures e corrupção desconhecida

Uma erasure é a ausência de um símbolo cuja posição é conhecida. Um pacote perdido ou rejeitado pelo CRC poderá ser representado assim em uma futura integração, desde que o índice do símbolo seja conhecido.

Requisitos:

- erasures devem ser representadas por índices;
- os índices devem estar no intervalo válido;
- não pode haver conflito entre um índice declarado como erasure e um símbolo recebido válido;
- símbolos recebidos devem ser identificados por índice;
- duplicatas devem ter comportamento definido e testado.

**Não assumir que a interface abstrata consegue detectar corrupção desconhecida.** Se um símbolo alterado chegar como se fosse válido, a API genérica não tem como saber disso sem um mecanismo adicional. A detecção de corrupção desconhecida deve continuar identificada como cenário separado, conforme `docs/error-control.md` e `docs/experiment-matrix.md`.

O contrato deve exigir que o chamador entregue somente símbolos considerados válidos, e declare como erasure os símbolos ausentes/rejeitados cuja posição seja conhecida.

## 6. Escolha da abstração Python

Inspecione os padrões do repositório e escolha uma solução idiomática para definir os contratos:

- `abc.ABC` com métodos abstratos; ou
- `typing.Protocol` com tipagem estrutural.

Não implemente as duas abordagens sem uma necessidade concreta. Registre a justificativa na documentação.

A API deve separar encoder e decoder, ainda que uma implementação concreta futura possa fornecer ambos. Os métodos devem ter type hints completos e docstrings que expliquem entrada, saída, erros e limites.

Nomes conceituais esperados:

- `FecConfig`;
- representação de símbolo;
- `EncodedBlock`;
- `DecodeResult`;
- contrato de encoder;
- contrato de decoder;
- exceção-base FEC e exceções específicas, se necessárias.

A localização provável é um pacote independente, por exemplo `src/meshmedia_lab/fec/`, mas confirme a estrutura atual antes de criar arquivos. Não coloque o algoritmo ou o contrato dentro de `protocol/packet.py`.

Não exporte classes na API pública do pacote principal sem necessidade. Se criar exports, mantenha `__all__` e testes coerentes.

## 7. Semântica de erros e limites

Documente e teste, no mínimo, os seguintes casos:

| Caso | Comportamento esperado |
|---|---|
| `algorithm_id` vazio ou inválido | Erro de configuração |
| `symbol_size <= 0` | Erro de configuração |
| `k <= 0` | Erro de configuração |
| `r < 0` | Erro de configuração |
| `n <= 0` | Erro de configuração |
| Relação inválida entre `n`, `k` e `r` | Erro de configuração, conforme invariável documentada |
| Profundidade negativa | Erro de configuração |
| Política desconhecida | Erro de configuração |
| Símbolo com índice negativo ou fora do bloco | Erro de entrada |
| Símbolo com tamanho incorreto | Erro de entrada |
| Índice duplicado | Erro de entrada ou regra explicitamente documentada; não ignorar silenciosamente |
| Índice declarado como erasure e também recebido | Erro de entrada |
| Quantidade insuficiente de símbolos | Resultado de falha de decodificação |
| Falha de recuperação | `success=False`, sem bytes parciais apresentados como bloco íntegro |
| Bloco final incompleto | Aplicar a política configurada ou rejeitar com erro documentado |

Não imponha ao contrato genérico o limite matemático de Reed-Solomon `2e + s <= n-k` como regra universal. Esse limite pertence à implementação RS e deve ser testado quando ela existir.

## 8. Testes obrigatórios desta issue

Crie testes unitários focados no contrato, sem dependência de algoritmo real.

Use uma implementação falsa/de teste (*fake*) que implemente a interface e permita verificar que:

- a interface pode ser implementada por uma classe independente;
- os métodos recebem os tipos definidos;
- o fluxo de codificação produz um `EncodedBlock` estruturalmente válido;
- o resultado pode ser entregue ao contrato de decodificação;
- o decoder pode informar sucesso e falha conforme o contrato;
- os metadados de comprimento original e padding são preservados;
- as validações de configuração funcionam;
- os índices e tamanhos dos símbolos são validados;
- erasures são aceitas quando válidas e rejeitadas quando inconsistentes;
- duplicatas e entradas malformadas têm comportamento determinístico;
- blocos incompletos respeitam a política configurada.

O fake não deve ser apresentado como FEC real. Seu objetivo é testar a interface, não demonstrar recuperação matemática.

Não escreva testes que dependam de RS, GF(2^8), polinômios ou limites de correção de erros. Isso pertence à próxima atividade (#20).

Execute a suíte existente e os testes específicos. O projeto aceita Python >= 3.10; mantenha compatibilidade com essa versão.

## 9. Documentação e rastreabilidade

Atualize os documentos afetados sem reescrever seções não relacionadas:

1. `docs/error-control.md`
   - substituir a indicação de que a interface é apenas conceitual pela descrição do contrato implementado;
   - registrar tipos, operações, semântica de falha, validações e limites;
   - manter Reed-Solomon como não implementado;
   - manter a separação CRC/FEC;
   - deixar explícito que ainda não há integração com MM1 ou transporte.

2. `docs/architecture.md`
   - registrar a camada FEC e sua posição arquitetural, sem sugerir integração funcional ao pipeline;
   - atualizar o mapeamento de componentes somente para arquivos que realmente existirem.

3. `docs/implementation-status.md`
   - marcar apenas a interface abstrata FEC como implementada se código, testes e documentação estiverem coerentes;
   - manter FEC funcional, Reed-Solomon, integração TX/RX e recuperação no pipeline como não implementados ou no estado já documentado;
   - não marcar a capacidade genérica de recuperação como implementada.

4. `sdd/sdd.md`
   - atualizar a Etapa C apenas no que foi realmente materializado;
   - preservar como propostas os parâmetros e decisões que ainda não foram fechados;
   - não declarar Reed-Solomon ou integração de protocolo como concluídos.

5. `CHANGELOG.md`
   - registrar a entrega do contrato abstrato, sem anunciar recuperação FEC funcional.

Se uma decisão técnica não puder ser fechada sem afetar compatibilidade ou semântica futura, documente a lacuna e pare para revisão humana em vez de inventar uma regra.

## 10. Compatibilidade e arquivos protegidos

A implementação desta issue não deve exigir mudanças no wire format.

Trate como protegidos contra alterações nesta atividade:

- `src/meshmedia_lab/protocol/packet.py`;
- `src/meshmedia_lab/protocol/descriptor.py`;
- `src/meshmedia_lab/protocol/fragmenter.py`;
- `src/meshmedia_lab/protocol/reassembler.py`;
- `src/meshmedia_lab/protocol/crc.py`;
- `src/meshmedia_lab/application/pipeline.py`;
- formato do Transmission Descriptor;
- cabeçalho MM1 v1 de 19 bytes;
- CRC-16/CCITT-FALSE de 2 bytes por pacote.

Se algum desses arquivos precisar ser alterado para concluir o contrato abstrato, não prossiga automaticamente. Explique a dependência e solicite revisão.

## 11. Sequência de execução recomendada

Execute nesta ordem:

1. Confirmar branch e estado limpo do repositório.
2. Ler os documentos obrigatórios e inspecionar os padrões Python existentes.
3. Identificar as decisões do contrato que já estão especificadas e as que continuam abertas.
4. Propor brevemente a organização dos módulos e os tipos públicos.
5. Implementar a configuração e suas validações.
6. Implementar tipos de símbolos e resultados.
7. Implementar as interfaces abstratas de encoder e decoder.
8. Implementar testes do contrato com fake.
9. Executar os testes específicos.
10. Executar a suíte completa disponível e ferramentas de lint configuradas, se instaladas.
11. Atualizar documentação, matriz de status e changelog com base somente no que foi implementado e testado.
12. Revisar o diff completo em busca de mudanças fora do escopo.
13. Abrir uma Pull Request vinculada à Issue #19 para revisão humana.

Não faça merge. Não feche a Issue #19 antes da revisão e da confirmação dos critérios de aceite.

## 12. Critérios de aceite — checklist final

- [ ] A API é independente de algoritmo FEC concreto.
- [ ] Configuração explícita, imutável e validada.
- [ ] Representação de símbolos com índice e tamanho definidos.
- [ ] Encoder e decoder possuem contratos abstratos distintos.
- [ ] `EncodedBlock` diferencia símbolos de origem e reparo.
- [ ] Padding e comprimento original têm semântica explícita.
- [ ] `DecodeResult` distingue sucesso de falha sem expor dados parciais como íntegros.
- [ ] Erasures têm semântica e validação definidas.
- [ ] Entradas inválidas e limites possuem comportamento testado.
- [ ] Testes utilizam fake, sem simular ou alegar implementação real de FEC.
- [ ] Nenhum algoritmo Reed-Solomon foi implementado.
- [ ] Nenhuma alteração incompatível no MM1 v1 foi feita.
- [ ] Nenhuma integração ao pipeline ou ao transporte foi feita.
- [ ] Documentação e status refletem exatamente o código existente.
- [ ] Testes executados foram registrados com seus resultados reais.
- [ ] Pull Request aberta para revisão, sem merge.

## 13. Relatório obrigatório ao final

Ao terminar, apresente:

1. resumo do contrato implementado;
2. decisão entre ABC ou Protocol e justificativa;
3. lista de arquivos criados/alterados;
4. decisões tomadas sobre padding, blocos incompletos, índices e falhas;
5. testes e comandos realmente executados, com resultados;
6. ferramentas não disponíveis ou testes não executados;
7. confirmação explícita de que MM1 v1, CRC, descritor, pipeline e transporte não foram alterados;
8. limitações que permanecem;
9. link da Pull Request.

**Próxima atividade após revisão:** Issue #20 — implementação experimental de Reed-Solomon. Não iniciar essa atividade dentro da Issue #19.
