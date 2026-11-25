const MESHCORE_JS_VERSION = "1.15.1";
const MESHCORE_MODULE_URL =
  "https://cdn.jsdelivr.net/npm/@liamcottle/meshcore.js@1.15.1/src/index.js";
const CONNECT_TIMEOUT_MS = 15_000;
const OPERATION_TIMEOUT_MS = 12_000;

const { Constants, WebSerialConnection } = await import(MESHCORE_MODULE_URL);

export { MESHCORE_JS_VERSION, MESHCORE_MODULE_URL };

export class MeshCoreAdapterError extends Error {
  constructor(message, code = "adapter-error") {
    super(message);
    this.name = "MeshCoreAdapterError";
    this.code = code;
  }
}

async function withTimeout(operation, timeoutMs, timeoutMessage) {
  let timer;
  try {
    return await Promise.race([
      operation,
      new Promise((_, reject) => {
        timer = setTimeout(() => {
          reject(new MeshCoreAdapterError(timeoutMessage, "timeout"));
        }, timeoutMs);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

function waitForConnected(connection) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const timer = setTimeout(() => {
      finish(
        new MeshCoreAdapterError(
          "O Companion não concluiu a inicialização USB/serial no tempo esperado.",
          "connect-timeout",
        ),
      );
    }, CONNECT_TIMEOUT_MS);

    const cleanup = () => {
      clearTimeout(timer);
      connection.off("connected", onConnected);
      connection.off("disconnected", onDisconnected);
    };

    const finish = (error) => {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      if (error) {
        reject(error);
      } else {
        resolve();
      }
    };

    const onConnected = () => finish();
    const onDisconnected = () =>
      finish(new MeshCoreAdapterError("O Companion desconectou durante a inicialização.", "disconnected"));

    connection.on("connected", onConnected);
    connection.on("disconnected", onDisconnected);
  });
}

export class MeshCoreSerialAdapter {
  constructor({ onMessage = () => {}, onStateChange = () => {}, onError = () => {} } = {}) {
    this.connection = null;
    this.channels = [];
    this.readingMessages = false;
    this.onMessage = onMessage;
    this.onStateChange = onStateChange;
    this.onError = onError;
    this.handleDisconnected = () => this.handleConnectionDisconnected();
    this.handleMessageWaiting = () => {
      void this.readMessages().catch((error) => this.handleOperationError(error));
    };
  }

  get isConnected() {
    return this.connection !== null;
  }

  async connect() {
    if (this.connection) {
      return this.connectionDetails();
    }

    this.emitState("connecting");
    let connection = null;
    try {
      connection = await WebSerialConnection.open();
      if (!connection) {
        throw new MeshCoreAdapterError(
          "A seleção da porta USB foi cancelada.",
          "cancelled",
        );
      }

      this.connection = connection;
      connection.on("disconnected", this.handleDisconnected);
      connection.on(Constants.PushCodes.MsgWaiting, this.handleMessageWaiting);
      await waitForConnected(connection);
      this.emitState("connected");
      return this.connectionDetails();
    } catch (error) {
      if (connection) {
        connection.off("disconnected", this.handleDisconnected);
        connection.off(Constants.PushCodes.MsgWaiting, this.handleMessageWaiting);
        try {
          await connection.close();
        } catch {
          // A failed initialization may not have a closable serial port.
        }
      }
      this.connection = null;
      this.channels = [];
      this.emitState("error", { error });
      throw error;
    }
  }

  async disconnect() {
    const connection = this.connection;
    if (!connection) {
      this.emitState("disconnected");
      return;
    }

    this.connection = null;
    this.channels = [];
    connection.off("disconnected", this.handleDisconnected);
    connection.off(Constants.PushCodes.MsgWaiting, this.handleMessageWaiting);
    try {
      await connection.close();
    } finally {
      this.emitState("disconnected");
    }
  }

  async listChannels() {
    const connection = this.requireConnection();
    const channels = await withTimeout(
      connection.getChannels(),
      OPERATION_TIMEOUT_MS,
      "A leitura dos canais demorou mais que o esperado.",
    );

    // Keep only public channel metadata. In particular, do not retain channel secrets.
    this.channels = channels.map((channel) => ({
      channelIdx: channel.channelIdx,
      name: channel.name || `Canal ${channel.channelIdx}`,
    }));
    return [...this.channels];
  }

  async sendText(channelIdx, text) {
    const connection = this.requireConnection();
    if (!Number.isInteger(channelIdx) || channelIdx < 0 || channelIdx > 255) {
      throw new MeshCoreAdapterError("Índice de canal inválido.", "invalid-channel");
    }
    if (typeof text !== "string" || text.trim().length === 0) {
      throw new MeshCoreAdapterError("Digite uma mensagem antes de enviar.", "empty-message");
    }

    await withTimeout(
      connection.sendChannelTextMessage(channelIdx, text.trim()),
      OPERATION_TIMEOUT_MS,
      "O Companion não confirmou o envio da mensagem.",
    );
  }

  async readMessages() {
    const connection = this.requireConnection();
    if (this.readingMessages) {
      return [];
    }

    this.readingMessages = true;
    try {
      const waitingMessages = await withTimeout(
        connection.getWaitingMessages(),
        OPERATION_TIMEOUT_MS,
        "A leitura das mensagens pendentes demorou mais que o esperado.",
      );
      const channelMessages = [];
      for (const waitingMessage of waitingMessages) {
        if (!waitingMessage?.channelMessage) {
          continue;
        }
        const message = {
          channelIdx: waitingMessage.channelMessage.channelIdx,
          text: waitingMessage.channelMessage.text,
          senderTimestamp: waitingMessage.channelMessage.senderTimestamp,
          snr: waitingMessage.channelMessage.snr,
          pathLen: waitingMessage.channelMessage.pathLen,
        };
        channelMessages.push(message);
        this.onMessage(message);
      }
      return channelMessages;
    } finally {
      this.readingMessages = false;
    }
  }

  connectionDetails() {
    const info = this.connection?.serialPort?.getInfo?.() || {};
    const identifiers = [];
    if (Number.isInteger(info.usbVendorId)) {
      identifiers.push(`VID 0x${info.usbVendorId.toString(16).padStart(4, "0")}`);
    }
    if (Number.isInteger(info.usbProductId)) {
      identifiers.push(`PID 0x${info.usbProductId.toString(16).padStart(4, "0")}`);
    }
    return {
      deviceName: identifiers.length
        ? `Companion USB/Serial (${identifiers.join(", ")})`
        : "Companion USB/Serial",
      libraryVersion: MESHCORE_JS_VERSION,
    };
  }

  requireConnection() {
    if (!this.connection) {
      throw new MeshCoreAdapterError("Conecte um Companion antes de continuar.", "not-connected");
    }
    return this.connection;
  }

  handleConnectionDisconnected() {
    if (!this.connection) {
      return;
    }
    this.connection = null;
    this.channels = [];
    this.emitState("disconnected");
  }

  handleOperationError(error) {
    this.onError(error);
    this.emitState("error", { error });
  }

  emitState(status, extra = {}) {
    this.onStateChange({
      status,
      deviceName: this.connectionDetails().deviceName,
      ...extra,
    });
  }
}
