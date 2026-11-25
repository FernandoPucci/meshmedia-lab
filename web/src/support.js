export function detectWebSerialSupport(runtime = globalThis) {
  const secureContext = runtime.isSecureContext === true;
  const webSerial =
    typeof runtime.navigator?.serial?.requestPort === "function";

  let message = "Web Serial disponível. Você pode selecionar uma porta USB.";
  if (!secureContext) {
    message = "Abra esta página em um contexto seguro HTTPS para usar Web Serial.";
  } else if (!webSerial) {
    message = "Este navegador não oferece Web Serial. Use Chrome ou Edge desktop.";
  }

  return {
    secureContext,
    webSerial,
    supported: secureContext && webSerial,
    message,
  };
}

export function formatConnectionError(error) {
  if (error?.code === "cancelled" || error?.name === "AbortError") {
    return "Seleção da porta USB cancelada.";
  }
  if (error?.name === "NotFoundError") {
    return "Nenhuma porta USB do Companion foi selecionada.";
  }
  if (error?.name === "SecurityError" || error?.name === "NotAllowedError") {
    return "O navegador bloqueou a permissão da porta serial neste contexto.";
  }
  if (error?.name === "NetworkError") {
    return "Não foi possível abrir ou manter a conexão USB/serial.";
  }
  if (error?.name === "InvalidStateError") {
    return "A porta USB já está conectada ou em uso por outra aplicação.";
  }
  if (error?.message) {
    return error.message;
  }
  return "Falha desconhecida na comunicação com o Companion.";
}
