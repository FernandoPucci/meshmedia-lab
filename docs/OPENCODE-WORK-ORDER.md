# Ordem de trabalho — evolucao do MeshMedia Lab

- **Objetivo:** orientar o OpenCode na evolucao incremental do MM1 a partir das decisoes de arquitetura acordadas em 2026-11-24.
- **Abordagem:** Specification-Driven Development (SDD).
- **Estado deste documento:** requisitos e plano de trabalho; as entregas das Issues #19, #20, #21 e #22 estao registradas na matriz de implementacao.
- **Baseline conhecida:** protocolo binario MM1 v1; implementacao Python 0.1.0; SDD 0.9.2-draft.
- **Limite inicial de imagem:** 128 x 128 pixels.

Este documento complementa o SDD e nao o substitui. Antes de alterar codigo, conferir o estado real da branch e os documentos atuais. Atualizar a matriz de implementacao e o changelog quando houver mudanca efetiva.

---

## 1. Decisoes confirmadas

### 1.1 Parametrizacao explicita, sem perfis predefinidos nesta fase

- A transmissao deve ser configuravel por parametros explicitos.
- Nao implementar agora catalogo de perfis fixos ou IDs de perfis predefinidos.
- Nao assumir que uma configuracao experimental sera uma configuracao recomendada para uso real.
- Registrar a configuracao efetivamente usada em cada experimento, para que os resultados sejam reproduziveis.
- Uma camada de perfis nomeados podera ser adicionada no futuro, sem ser requisito desta etapa.

### 1.2 Dimensoes de imagem

- A largura e a altura devem ser parametros independentes.
- O limite maximo inicial e **128 pixels de largura por 128 pixels de altura**.
- Sao permitidas imagens nao quadradas, desde que cada dimensao respeite o limite.
- A validacao deve rejeitar dimensoes acima do limite, com erro claro.
- Nao introduzir nesta etapa composicao automatica de imagens maiores.

### 1.3 Codecs e representacao

- Manter grayscale como caminho de referencia existente.
- Projetar identificadores explicitos e estaveis para os codecs, evitando depender de configuracao escondida no transmissor.
- Preparar a arquitetura para grayscale e colorido.
- RGB332 foi o candidato inicial para representacao colorida compacta; apos a
  validacao da Issue #38, seus parametros e forma de empacotamento estao
  implementados sem alterar o layout MM1 v1.
- O receptor deve conseguir interpretar a representacao a partir dos metadados/descritor recebidos.
- Compressao (incluindo RLE) deve ser identificada separadamente do formato de cor/codec, caso essa separacao seja adotada no desenho. Nao presumir que RLE ja esteja implementado.

### 1.4 Transmission Descriptor

Atualizacao apos a PR #42: o ADR 0004 fecha o contrato inline da Issue #17,
autorizado para implementacao em branch apartada apos a apresentacao da proposta.
Usar flag `0x04`, marcador `TD`, corpo v1 big-endian fixo de 16 bytes,
encoded_length uint32 obrigatorio e comparacao estrita de metadados duplicados.
O modo legado e seu default permanecem inalterados. A proposta anterior da
Etapa A de nao repetir metadados e substituida por essa decisao rastreavel.
FEC continua sem campos no corpo do descritor; as Issues #21/#22 adicionaram
uma extensao opt-in separada com `FLAG_FEC=0x08` e frames `FC`. Futuras
alteracoes do descritor exigem nova revisao.
Os itens a seguir registram a ordem original da Etapa A, ja materializada
no contrato `docs/transmission-descriptor.md`:

- Especificar um descritor de transmissao enviado no inicio de cada transmissao.
- O descritor deve informar ao receptor os parametros necessarios para interpretar os dados sem depender de configuracao local compartilhada.
- Avaliar quais parametros precisam estar no descritor e quais podem estar nos pacotes/blocos.
- Evitar repetir metadados invariantes em todos os fragmentos quando isso puder ser resolvido com um descritor e identificador de transmissao.
- Definir identificador de transmissao e regras para associar descritor, fragmentos e blocos.
- Definir comportamento para descritor ausente, duplicado, invalido ou recebido fora de ordem.
- Nao fixar o wire format antes de documentar campos, tamanhos, endianness, validacao, compatibilidade e limites de payload.

### 1.5 CRC e FEC

- Preservar CRC-16/CCITT-FALSE como baseline implementada no MM1 v1.
- Projetar uma interface abstrata de FEC, independente do algoritmo concreto.
- Reed-Solomon sera o primeiro candidato experimental, nao uma escolha definitiva para producao.
- A configuracao experimental deve permitir selecionar algoritmo e parametros, incluindo, quando aplicavel: FEC habilitado/desabilitado; algoritmo; tamanho do simbolo; simbolos de dados (k); simbolos de paridade/reparo; tamanho do bloco; interleaving; politica de preenchimento e tratamento de blocos incompletos.
- Diferenciar claramente simbolo FEC, bloco FEC, fragmento MM1 e payload do transporte.
- Estudar combinacoes CRC + FEC, somente CRC e somente FEC. Um modo sem CRC pode ser usado em experimento controlado, mas nao pode ser introduzido no MM1 v1 por alteracao silenciosa.
- Documentar como pacotes perdidos ou rejeitados pelo CRC serao identificados como erasures para o decodificador FEC.
- CRC detecta corrupcao; FEC pode recuperar dados. Nao tratar os mecanismos como equivalentes.
- A interface deve permitir outros algoritmos FEC no futuro, sem acoplar o protocolo ao Reed-Solomon.

### 1.6 Compatibilidade do protocolo

- O formato binario MM1 v1 existente possui cabecalho de 19 bytes e CRC de 2 bytes por pacote.
- Nao alterar silenciosamente campos, tamanhos ou semantica do MM1 v1.
- Se o descritor, os identificadores de bloco FEC ou a configuracao flexivel exigirem campos que nao cabem no formato atual, especificar uma extensao compativel ou uma nova versao do protocolo.
- A decisao deve considerar coexistencia, deteccao de versao, comportamento de TX/RX incompativeis e testes com vetores binarios.
- Nao declarar compatibilidade antes de haver especificacao e testes.

### 1.7 Metricas e benchmarks

As metricas pertencem ao laboratorio de testes e benchmarks. Nao sao, por padrao, campos do protocolo nem dados que precisem ser transmitidos ao receptor.

- Primeira etapa: testes locais, inicialmente com transporte em memoria e UDP.
- Etapa posterior: usar a mesma abordagem de medicao durante testes com placas LoRa/MeshCore.
- Registrar configuracao, seed, numero de repeticoes e versoes utilizadas.
- Separar resultados de simulacao local de resultados medidos em radio real.
- Medir, conforme aplicavel: bytes de origem, bytes codificados, bytes de reparo, bytes transmitidos, overhead, quantidade de pacotes, perdas, corrupcoes detectadas, simbolos recuperados, sucesso de reconstrucao, tempos de encode/decode/reassemblagem e airtime estimado/medido.
- PSNR/SSIM podem ser avaliados para comparar qualidade visual quando houver transformacao com perda.
- Nao inserir instrumentacao ou telemetria de benchmark no wire format sem justificativa independente.

### 1.8 Separacao dos transportes

O protocolo e os codecs nao devem depender de UDP ou MeshCore.

- UDP e transporte de laboratorio, util para testes locais e benchmarks.
- MeshCore sera um adaptador de transporte separado, sujeito aos limites reais de payload, serializacao, canal, roteamento e airtime.
- Os dois adaptadores podem ter estrategias e parametros operacionais distintos, sem alterar a semantica dos dados MM1.
- Nao assumir que o UDP local representa fielmente o comportamento da rede LoRa.

---

## 2. Plano de trabalho — executar em incrementos

### Etapa A — especificacao antes do codigo

1. Revisar o SDD e criar/atualizar a especificacao de configuracao de transmissao parametrizada.
2. Especificar o Transmission Descriptor: ciclo de vida, campos, validacao, associacao com fragmentos e comportamento em falhas/ordem de chegada.
3. Definir o registro de codecs: identificadores, parametros, dimensoes e representacoes grayscale/color.
4. Definir a interface abstrata de FEC e o contrato de entrada/saida dos codificadores e decodificadores.
5. Definir como CRC e FEC podem ser combinados nos experimentos, sem quebrar o MM1 v1.
6. Apresentar uma decisao de compatibilidade: extensao do formato atual ou nova versao. Nao implementar wire format novo antes dessa decisao estar documentada.
7. Atualizar diagramas, arquitetura e matriz de rastreabilidade.

**Entregaveis minimos sugeridos:**
- docs/transmission-profile.md — parametros e validacoes da transmissao; nesta fase descreve configuracao explicita, nao perfis predefinidos.
- docs/transmission-descriptor.md — proposta do descritor e ciclo de vida.
- docs/experiment-matrix.md — cenarios e metricas dos benchmarks locais e, futuramente, de hardware.
- Atualizacoes em sdd/sdd.md, docs/architecture.md e docs/implementation-status.md.

**Criterio de aceite:** documentos coerentes entre si, sem contradizer o MM1 v1 existente; campos e limites propostos claramente separados dos campos implementados. Parar para revisao humana antes de alterar o wire format.

### Etapa B — codecs e dimensoes

1. Preservar o codec grayscale atual e seus testes.
2. Ajustar a API para largura e altura independentes, com limite maximo de 128 x 128.
3. Implementar testes para dimensoes minimas, nao quadradas, 128 x 128 e rejeicao de dimensoes acima do limite.
4. Implementar RGB332 somente depois de especificar identificador, ordem dos canais, empacotamento e reconstrucao. Essa condicao foi satisfeita pela Issue #38.
5. Testar round-trip, limites, dados truncados e identificadores desconhecidos.

**Criterio de aceite:** TX e RX interpretam a representacao pelos metadados/descritor; testes automatizados cobrem grayscale e RGB332; nenhum teste ou exemplo sugere suporte a resolucoes maiores que 128 x 128 nesta fase.

### Etapa C — controle de erros parametrizavel

1. Extrair/organizar CRC e FEC sem quebrar a implementacao CRC atual.
2. Definir contratos abstratos para encoder/decoder FEC.
3. Implementar Reed-Solomon como primeiro plugin/implementacao experimental.
4. Integrar preparacao TX, frames opt-in e recuperacao RX nas Issues #21/#22.
5. Cobrir casos de ausencia, corrupcao, erasures, erros desconhecidos, preenchimento e blocos incompletos.
6. Comparar CRC-only, CRC + RS e RS-only em ambiente controlado. O modo RS-only e experimental e nao altera o caminho legado.
7. Nao selecionar uma configuracao vencedora sem resultados reproduziveis.

**Criterio de aceite:** testes unitarios do algoritmo, testes de integracao do pipeline e vetores conhecidos; parametros completos registrados em cada execucao.

### Etapa D — laboratorio de benchmarks local

1. Criar um executor de cenarios reproduziveis para UDP e/ou memoria.
2. Manter simulacao local separada do adaptador de transporte.
3. Registrar seeds e repeticoes.
4. Produzir resultados em formato legivel por maquina (por exemplo JSON/CSV) e um resumo humano.
5. Comparar baseline sem FEC com configuracoes FEC, mantendo iguais imagem, codec, resolucao, payload e condicoes do canal.
6. Separar metricas de qualidade visual das metricas de transporte.

**Criterio de aceite:** um benchmark pode ser repetido com a mesma configuracao/seed e produz resultados comparaveis; os resultados identificam claramente que foram obtidos em ambiente local simulado.

### Etapa E — integracao futura com MeshCore

Esta etapa depende da conclusao e validacao das etapas anteriores. Nao executar agora sem solicitacao explicita.

Plano de teste desejado:
1. Conectar duas placas LoRa/MeshCore a duas portas seriais distintas do mesmo PC.
2. Executar um processo/aplicacao de TX associado a uma porta e um processo/aplicacao de RX associado a outra.
3. Enviar uma mensagem de teste dentro de um canal MeshCore criptografado.
4. Depois de validar o transporte de mensagens, transportar fragmentos MM1.
5. Medir comportamento real: bytes aceitos, fragmentos enviados/recebidos, perdas, tempos e reconstrucao.
6. Respeitar os limites reais de payload e o comportamento do MeshCore.

**Restricao inicial:** tentar a integracao usando o firmware MeshCore existente e suas interfaces seriais/protocolos disponiveis. Nao modificar firmware como primeira opcao. Se a interface existente nao permitir o fluxo necessario, documentar a limitacao e apresentar alternativas antes de customizar firmware.

**Criterio de aceite:** teste reproduzivel com duas placas, canal criptografado, TX/RX identificados e evidencia de reconstrucao no PC receptor. Resultados de radio real devem ser rotulados separadamente dos benchmarks UDP.

---

## 3. Itens explicitamente futuros — nao implementar nesta rodada

### 3.1 Imagens maiores por tiles

No futuro, imagens com dimensoes superiores a 128 x 128 poderao ser divididas em uma grade de tiles de ate 128 x 128, transmitidos e remontados como uma imagem maior.

A ideia e semelhante, em nivel conceitual, a transmissao segmentada de imagens encontrada em solucoes como Icom D-STAR/RS-MS1A. Isso e uma referencia de inspiracao, nao uma exigencia de compatibilidade ou de reproduzir o protocolo do Icom.

Possiveis beneficios a estudar:
- transmitir e reconstruir cada tile independentemente;
- detectar e recuperar falhas por regiao;
- retransmitir somente tiles ausentes;
- priorizar regioes;
- permitir refinamento progressivo.

Nao implementar tiling, coordenadas de tiles ou remontagem de imagem grande nesta rodada.

### 3.2 Perfis predefinidos

Perfis nomeados podem facilitar operacao embarcada no futuro. Por enquanto, usar parametros explicitos e registrar a configuracao completa. Nao criar IDs de perfis nem presets como requisito atual.

### 3.3 Transmissao progressiva

Camadas de refinamento, prioridade de blocos e apresentacao parcial da imagem permanecem futuras.

### 3.4 Firmware customizado

Nao modificar firmware MeshCore como primeiro caminho. Primeiro avaliar as interfaces seriais e recursos ja existentes.


### 3.5 WebApp browser-only TX/RX — objetivo de produto

Rastreabilidade: [Issue #39](https://github.com/FernandoPucci/meshmedia-lab/issues/39)
e SDD, seção 29.

Construir uma aplicação web estática publicada em GitHub Pages (HTTPS). O
usuário abre um link no navegador e conecta diretamente ao MeshCore Companion
por Web Serial/USB. Não deve ser necessário instalar Python, Docker ou qualquer serviço,
clonar o repositório, nem iniciar backend/servidor local.

**Regra inviolável: reutilizar o codec existente.** A WebApp deverá executar e
consumir a implementação Python já existente em src/meshmedia_lab/codec/,
sem reescrever, portar, alterar APIs, ajustar algoritmos ou duplicar os codecs.
Pyodide/WebAssembly é a hipótese inicial para executar o Python no navegador.
A prova de conceito deve comprovar essa execução com os testes/vetores atuais.
Se não for possível sem modificar o codec, parar e apresentar alternativas
para decisão humana. Adaptadores, wrappers e UI novos devem ficar fora dos
módulos existentes de codec.

- Frontend browser-only para upload, preview, dimensões, codec, estimativas,
  progresso e imagem recebida.
- Usar `WebSerialConnection` de meshcore.js para conexão USB com o Companion;
  confirmar API, licença, notificações e envio de dados binários antes de
  fixar dependência.
- Manter o firmware Companion compatível com USB como caminho primário desta
  PoC. Web Bluetooth é alternativa futura, não pré-requisito.
- Processar imagem, codec, preparação MM1, recepção e decodificação localmente
  no navegador. GitHub Pages entrega apenas assets estáticos.
- Duas estações independentes abrem a mesma aplicação hospedada e conectam
  cada uma seu próprio Companion.
- Chrome/Edge desktop com HTTPS e Web Serial é a plataforma inicial. Detectar
  suporte ausente; validar Linux cedo e não anunciar Firefox/Safari sem
  adaptador alternativo comprovado.
- Preservar wire format MM1 v1, o codec e os testes existentes. Respeitar os
  limites atuais: grayscale 128 x 128 e RGB332 64 x 64.
- Manter criptografia e chaves sob responsabilidade do MeshCore. Não registrar
  material criptográfico.
- FEC continua opt-in; ACK/NACK, retransmissão de aplicação e transmissão
  progressiva não devem ser apresentados como disponíveis.

**Ordem de execução recomendada:**
1. Prova de conceito estática em GitHub Pages/HTTPS e detecção Web Serial.
2. Conexão USB/serial ao Companion e leitura de informações básicas.
3. Seleção de canal e envio/recepção de uma mensagem de texto comum pelo
   mecanismo normal do Companion. Essa mensagem é somente um teste funcional e
   não transporta bytes MM1.
4. Prova de execução do codec Python existente via Pyodide/WebAssembly, sem
   alterar os arquivos do codec; conferir os vetores/testes de referência.
5. Adaptador browser Web Serial para o mecanismo binário de grupo e para o pipeline
   MM1 existente, com validação do limite real de payload.
6. Só então evoluir para UI TX/RX de imagens e ensaio ponta a ponta com duas
   Heltec V3.

**Dependências:** a prova de conceito pode começar antes da conclusão de toda a
Etapa E, pois serve para validar riscos técnicos de navegador e Web Serial. A
transmissão real de imagens continua condicionada à validação do transporte,
do payload binário de grupo e do ensaio com duas placas. A WebApp não substitui
essas validações.

**Estado:** a PoC incremental de serial/texto está implementada em `web/`, mas o
aceite com hardware real ainda não foi demonstrado. Codec no browser,
transporte binário, MM1 e transmissão de imagens permanecem não implementados.
---

## 4. Regras de engenharia para o OpenCode

- Trabalhar em uma atividade pequena por vez.
- Antes de codificar, inspecionar os modulos e testes existentes; nao presumir que a estrutura sugerida em conversas anteriores ja exista.
- Evitar refatoracao ampla ou renomeacao em massa.
- Preservar a API publica quando possivel; documentar qualquer quebra.
- Nao adicionar dependencia externa sem justificar necessidade, manutencao e compatibilidade.
- Nao confundir limite de frame MeshCore com payload disponivel para dados de aplicacao. Consultar docs/meshcore-reference.md.
- Nao afirmar que o MM1 ja funciona em MeshCore: a integracao real ainda e futura.
- Atualizar docs/implementation-status.md somente com evidencia de codigo e testes.
- Atualizar CHANGELOG.md com mudancas documentais e de comportamento.
- Executar os testes relevantes e, ao final, a suite completa disponivel.
- Se uma decisao afetar compatibilidade binaria, seguranca, criptografia ou transporte real, parar e apresentar alternativas para revisao humana.

## 5. Relatorio esperado ao concluir cada etapa

O OpenCode deve apresentar:
1. objetivo da etapa;
2. arquivos criados/alterados;
3. decisoes tecnicas e justificativas;
4. testes executados e resultados reais;
5. limitacoes conhecidas;
6. itens ainda nao implementados;
7. proxima atividade recomendada.

Nao marcar uma etapa como concluida se seus criterios de aceite nao tiverem sido verificados.
