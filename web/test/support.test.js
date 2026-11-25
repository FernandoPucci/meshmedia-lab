import assert from "node:assert/strict";
import test from "node:test";

import { detectWebBluetoothSupport, formatConnectionError } from "../src/support.js";

test("detects a secure context with Web Bluetooth", () => {
  const result = detectWebBluetoothSupport({
    isSecureContext: true,
    navigator: { bluetooth: {} },
  });

  assert.deepEqual(result, {
    secureContext: true,
    webBluetooth: true,
    supported: true,
    message: "Web Bluetooth disponível. Você pode solicitar a conexão.",
  });
});

test("reports an insecure context before browser support", () => {
  const result = detectWebBluetoothSupport({
    isSecureContext: false,
    navigator: { bluetooth: {} },
  });

  assert.equal(result.supported, false);
  assert.match(result.message, /HTTPS/);
});

test("reports missing Web Bluetooth", () => {
  const result = detectWebBluetoothSupport({
    isSecureContext: true,
    navigator: {},
  });

  assert.equal(result.supported, false);
  assert.match(result.message, /não oferece Web Bluetooth/);
});

test("maps expected browser connection errors to user guidance", () => {
  assert.equal(
    formatConnectionError({ name: "AbortError" }),
    "Seleção do dispositivo cancelada.",
  );
  assert.equal(
    formatConnectionError({ name: "SecurityError" }),
    "O navegador bloqueou a permissão Bluetooth neste contexto.",
  );
  assert.equal(
    formatConnectionError({ message: "erro de teste" }),
    "erro de teste",
  );
});
