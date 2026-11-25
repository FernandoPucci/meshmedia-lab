import { detectWebSerialSupport, formatConnectionError } from "./support.js";

const elements = {
  supportBadge: document.querySelector("#support-badge"),
  supportStatus: document.querySelector("#support-status"),
  connectButton: document.querySelector("#connect-button"),
  disconnectButton: document.querySelector("#disconnect-button"),
  connectionBadge: document.querySelector("#connection-badge"),
  connectionStatus: document.querySelector("#connection-status"),
  deviceName: document.querySelector("#device-name"),
  refreshChannelsButton: document.querySelector("#refresh-channels-button"),
  channelSelect: document.querySelector("#channel-select"),
  channelStatus: document.querySelector("#channel-status"),
  messageForm: document.querySelector("#message-form"),
  messageInput: document.querySelector("#message-input"),
  sendButton: document.querySelector("#send-button"),
  receiveButton: document.querySelector("#receive-button"),
  messageStatus: document.querySelector("#message-status"),
  receivedMessage: document.querySelector("#received-message"),
  receivedMeta: document.querySelector("#received-meta"),
  activityLog: document.querySelector("#activity-log"),
};

const support = detectWebSerialSupport();
let adapter = null;
let adapterModulePromise = null;
let channels = [];
let connectionState = "disconnected";

function setBadge(element, label, variant = "neutral") {
  element.textContent = label;
  element.className = `badge badge-${variant}`;
}

function addActivity(message) {
  const item = document.createElement("li");
  item.textContent = message;
  elements.activityLog.append(item);
  while (elements.activityLog.children.length > 40) {
    elements.activityLog.firstElementChild.remove();
  }
  elements.activityLog.scrollTop = elements.activityLog.scrollHeight;
}

function selectedChannel() {
  if (!elements.channelSelect.value) {
    return null;
  }
  return channels.find(
    (channel) => String(channel.channelIdx) === elements.channelSelect.value,
  ) || null;
}

function updateControls() {
  const connected = connectionState === "connected";
  const busy = connectionState === "connecting";
  const hasChannel = selectedChannel() !== null;

  elements.connectButton.disabled = !support.supported || connected || busy;
  elements.disconnectButton.disabled = !connected && !busy;
  elements.refreshChannelsButton.disabled = !connected;
  elements.channelSelect.disabled = !connected || channels.length === 0;
  elements.messageInput.disabled = !connected || !hasChannel;
  elements.sendButton.disabled = !connected || !hasChannel;
  elements.receiveButton.disabled = !connected;
}

function setConnectionState(state, details = {}) {
  connectionState = state.status || state;
  const labels = {
    connecting: ["Conectando…", "warning", "Conectando ao Companion…"],
    connected: ["Conectado", "success", "Companion conectado"],
    disconnected: ["Desconectado", "neutral", "Aguardando conexão"],
    error: ["Erro", "error", "A conexão precisa ser verificada"],
  };
  const [label, variant, statusText] = labels[connectionState] || labels.disconnected;
  setBadge(elements.connectionBadge, label, variant);
  elements.connectionStatus.textContent = statusText;
  if (details.deviceName && connectionState === "connected") {
    elements.deviceName.textContent = details.deviceName;
  }
  if (connectionState === "disconnected" || connectionState === "error") {
    elements.deviceName.textContent = "Nenhum dispositivo conectado";
    channels = [];
    elements.channelSelect.replaceChildren(
      new Option("Conecte-se para carregar os canais", ""),
    );
    elements.channelStatus.textContent = "Nenhum canal carregado.";
  }
  updateControls();
}

function setSupportState() {
  elements.supportStatus.textContent = support.message;
  if (support.supported) {
    setBadge(elements.supportBadge, "Disponível", "success");
  } else {
    setBadge(elements.supportBadge, "Indisponível", "error");
  }
  updateControls();
}

async function getAdapter() {
  if (!adapterModulePromise) {
    adapterModulePromise = import("./meshcore-adapter.js");
  }
  const module = await adapterModulePromise;
  if (!adapter) {
    adapter = new module.MeshCoreSerialAdapter({
      onMessage: handleIncomingMessage,
      onStateChange: setConnectionState,
      onError: (error) => addActivity(`Erro de recepção: ${formatConnectionError(error)}`),
    });
  }
  return adapter;
}

async function connect() {
  if (!support.supported) {
    return;
  }
  setConnectionState({ status: "connecting" });
  elements.messageStatus.textContent = "Solicitando seleção da porta USB…";
  try {
    const meshCoreAdapter = await getAdapter();
    const details = await meshCoreAdapter.connect();
    elements.deviceName.textContent = details.deviceName;
    addActivity(`Conectado ao dispositivo ${details.deviceName}.`);
    await refreshChannels();
  } catch (error) {
    const message = formatConnectionError(error);
    elements.messageStatus.textContent = message;
    addActivity(`Falha de conexão: ${message}`);
  } finally {
    updateControls();
  }
}

async function disconnect() {
  if (!adapter) {
    return;
  }
  try {
    await adapter.disconnect();
    addActivity("Desconectado do Companion.");
  } catch (error) {
    const message = formatConnectionError(error);
    elements.messageStatus.textContent = message;
    addActivity(`Falha ao desconectar: ${message}`);
  }
}

async function refreshChannels() {
  if (!adapter || !adapter.isConnected) {
    return;
  }
  elements.channelStatus.textContent = "Lendo canais do Companion…";
  elements.refreshChannelsButton.disabled = true;
  try {
    channels = await adapter.listChannels();
    elements.channelSelect.replaceChildren(
      new Option(
        channels.length ? "Selecione um canal" : "Nenhum canal disponível",
        "",
      ),
    );
    for (const channel of channels) {
      elements.channelSelect.append(
        new Option(`${channel.name} (índice ${channel.channelIdx})`, channel.channelIdx),
      );
    }
    elements.channelStatus.textContent = channels.length
      ? `${channels.length} canal(is) disponível(is).`
      : "O Companion não retornou canais configurados.";
    addActivity(
      channels.length
        ? `${channels.length} canal(is) carregado(s).`
        : "Nenhum canal configurado foi encontrado.",
    );
  } catch (error) {
    const message = formatConnectionError(error);
    elements.channelStatus.textContent = message;
    addActivity(`Falha ao carregar canais: ${message}`);
  } finally {
    updateControls();
  }
}

async function sendMessage(event) {
  event.preventDefault();
  const channel = selectedChannel();
  const text = elements.messageInput.value.trim();
  if (!channel || !text || !adapter) {
    elements.messageStatus.textContent = "Selecione um canal e digite uma mensagem.";
    return;
  }

  elements.sendButton.disabled = true;
  elements.messageStatus.textContent = "Enviando mensagem…";
  try {
    await adapter.sendText(channel.channelIdx, text);
    elements.messageInput.value = "";
    elements.messageStatus.textContent = "Mensagem enviada pelo Companion.";
    addActivity(`Mensagem enviada no canal ${channel.name}.`);
  } catch (error) {
    const message = formatConnectionError(error);
    elements.messageStatus.textContent = message;
    addActivity(`Falha no envio: ${message}`);
  } finally {
    updateControls();
  }
}

async function receiveMessages() {
  if (!adapter || !adapter.isConnected) {
    return;
  }
  elements.receiveButton.disabled = true;
  elements.messageStatus.textContent = "Verificando mensagens pendentes…";
  try {
    const messages = await adapter.readMessages();
    elements.messageStatus.textContent = messages.length
      ? `${messages.length} mensagem(ns) recebida(s).`
      : "Nenhuma mensagem pendente.";
    if (!messages.length) {
      addActivity("Nenhuma mensagem pendente no Companion.");
    }
  } catch (error) {
    const message = formatConnectionError(error);
    elements.messageStatus.textContent = message;
    addActivity(`Falha na recepção: ${message}`);
  } finally {
    updateControls();
  }
}

function handleIncomingMessage(message) {
  const channel = channels.find((item) => item.channelIdx === message.channelIdx);
  const channelName = channel?.name || `índice ${message.channelIdx}`;
  elements.receivedMessage.textContent = message.text || "(mensagem vazia)";
  elements.receivedMeta.textContent = `Canal ${channelName}. A mensagem foi mantida somente em memória nesta página.`;
  elements.messageStatus.textContent = "Mensagem de canal recebida.";
  addActivity(`Mensagem recebida no canal ${channelName}.`);
}

elements.connectButton.addEventListener("click", () => void connect());
elements.disconnectButton.addEventListener("click", () => void disconnect());
elements.refreshChannelsButton.addEventListener("click", () => void refreshChannels());
elements.channelSelect.addEventListener("change", () => {
  const channel = selectedChannel();
  elements.messageStatus.textContent = channel
    ? `Canal selecionado: ${channel.name} (índice ${channel.channelIdx}).`
    : "Selecione um canal para habilitar o envio.";
  updateControls();
});
elements.messageForm.addEventListener("submit", (event) => void sendMessage(event));
elements.receiveButton.addEventListener("click", () => void receiveMessages());

window.addEventListener("beforeunload", () => {
  if (adapter) {
    void adapter.disconnect();
  }
});

setSupportState();
setConnectionState({ status: "disconnected" });
