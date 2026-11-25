export function detectWebBluetoothSupport(runtime = globalThis) {
  const secureContext = runtime.isSecureContext === true;
  const webBluetooth =
    Boolean(runtime.navigator) && "bluetooth" in runtime.navigator;

  let message = "Web Bluetooth disponível. Você pode solicitar a conexão.";
  if (!secureContext) {
    message = "Abra esta página em um contexto seguro HTTPS para usar Bluetooth.";
  } else if (!webBluetooth) {
    message = "Este navegador não oferece Web Bluetooth. Use Chrome ou Edge desktop.";
  }

  return {
    secureContext,
    webBluetooth,
    supported: secureContext && webBluetooth,
    message,
  };
}

export function formatConnectionError(error) {
  if (error?.code === "cancelled" || error?.name === "AbortError") {
    return "Seleção do dispositivo cancelada.";
  }
  if (error?.name === "NotFoundError") {
    return "Nenhum dispositivo Companion foi selecionado.";
  }
  if (error?.name === "SecurityError") {
    return "O navegador bloqueou a permissão Bluetooth neste contexto.";
  }
  if (error?.name === "NetworkError") {
    return "Não foi possível estabelecer ou manter a conexão Bluetooth.";
  }
  if (error?.name === "InvalidStateError") {
    return "O dispositivo já está conectado ou em uso por outra aplicação.";
  }
  if (error?.message) {
    return error.message;
  }
  return "Falha desconhecida na comunicação com o Companion.";
}
