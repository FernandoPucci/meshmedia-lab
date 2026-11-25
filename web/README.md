# MeshMedia Lab WebApp — PoC USB/Serial

Esta pasta contém a primeira PoC browser-only do MeshMedia Lab.

## Escopo desta PoC

- página estática;
- detecção de contexto seguro e `navigator.serial`;
- conexão USB ao firmware MeshCore Companion por Web Serial;
- leitura dos canais disponíveis;
- envio e recepção de mensagens de texto comuns;
- diagnóstico somente em memória no navegador.

Esta entrega **não** implementa codec, Pyodide, MM1, FEC, reassemblagem ou
transporte binário. A mensagem de texto é somente um teste funcional do
Companion e não deve carregar bytes MM1.

## Dependência avaliada

A integração usa, por enquanto, um import ESM versionado da biblioteca
[`@liamcottle/meshcore.js`](https://github.com/meshcore-dev/meshcore.js), versão
`1.15.1`, sob licença MIT. A versão está fixada na URL do
`src/meshcore-adapter.js`; nenhum segredo, mensagem ou dado de mídia é enviado
para o CDN.

A biblioteca foi escolhida porque expõe `WebSerialConnection`, `getChannels()`,
`sendChannelTextMessage()` e `getWaitingMessages()`. A conexão é aberta a
`115200` baud pelo protocolo serial do Companion. O envio binário
`sendChannelData()` não é usado nesta PoC.

O uso via ESM remoto evita introduzir um bundler ou dependências de build antes
de comprovar o fluxo USB/serial. Antes da integração MM1, a dependência deverá ser
reavaliada quanto a bundle browser, política de carregamento, versão fixada e
limites reais do Companion.

## Execução local para desenvolvimento

O usuário final não precisa executar servidor local. Para desenvolvimento, uma
página servida por `localhost` é aceita pelo navegador como contexto seguro:

```bash
python3 -m http.server 8000 --directory web
```

Abra `http://localhost:8000/` em Chrome ou Edge desktop. O dispositivo precisa
estar executando o firmware MeshCore Companion compatível com USB/serial e estar
conectado por USB. O caminho upstream correspondente é documentado como
`companion_radio_usb`.

## Publicação

O workflow `deploy-webapp.yml` publica o conteúdo desta pasta no GitHub Pages
quando a branch `master` recebe a alteração. O repositório precisa estar
configurado para usar **GitHub Actions** como fonte do Pages.

## Ensaio manual com hardware

Registrar pelo menos:

- modelo da placa e versão/build do firmware Companion USB;
- sistema operacional e versão do Chrome/Edge;
- versão `@liamcottle/meshcore.js`;
- identificação USB da porta, quando exibida pelo navegador;
- índices/nomes dos canais usados, sem registrar segredos;
- estação transmissora e receptora;
- texto enviado, horário e resultado observado;
- desconexões ou erros.

O aceite da PoC exige duas estações MeshCore reais. Testes com mock não
comprovam conexão Web Serial nem entrega pelo rádio.
