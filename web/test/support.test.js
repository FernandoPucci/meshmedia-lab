import assert from "node:assert/strict";
import test from "node:test";

import { detectWebSerialSupport, formatConnectionError } from "../src/support.js";

test("detects a secure context with Web Serial", () => {
  const result = detectWebSerialSupport({
    isSecureContext: true,
    navigator: { serial: { requestPort: () => {} } },
  });

  assert.deepEqual(result, {
    secureContext: true,
    webSerial: true,
    supported: true,
    message: "Web Serial disponível. Você pode selecionar uma porta USB.",
  });
});

test("reports an insecure context before browser support", () => {
  const result = detectWebSerialSupport({
    isSecureContext: false,
    navigator: { serial: { requestPort: () => {} } },
  });

  assert.equal(result.supported, false);
  assert.match(result.message, /HTTPS/);
});

test("reports missing Web Serial", () => {
  const result = detectWebSerialSupport({
    isSecureContext: true,
    navigator: {},
  });

  assert.equal(result.supported, false);
  assert.match(result.message, /não oferece Web Serial/);
});

test("maps expected browser connection errors to user guidance", () => {
  assert.equal(
    formatConnectionError({ name: "AbortError" }),
    "Seleção da porta USB cancelada.",
  );
  assert.equal(
    formatConnectionError({ name: "SecurityError" }),
    "O navegador bloqueou a permissão da porta serial neste contexto.",
  );
  assert.equal(
    formatConnectionError({ message: "erro de teste" }),
    "erro de teste",
  );
});
