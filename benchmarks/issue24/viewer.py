"""Small local side-by-side viewer for Issue #24 result artifacts."""

from __future__ import annotations

import argparse
import html
import json
import mimetypes
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .config import SCENARIOS
from .fixtures import build_fixture, generate_reference_images
from .report import write_reports
from .runner import (
    FIXTURE_IDS,
    execute_one,
    write_result_indexes,
)

STRATEGY_IDS = (
    "crc-only",
    "crc+rs-rs32-28-4",
    "crc+rs-rs32-24-8",
    "crc+rs-rs32-20-12",
    "rs-only-rs32-28-4",
    "rs-only-rs32-24-8",
    "rs-only-rs32-20-12",
)
RESOLUTION_IDS = ("32x32", "64x64", "128x128")


def _resampling_filter(image_module, name: str):
    resampling = getattr(image_module, "Resampling", image_module)
    return getattr(resampling, name)


class ResultCatalog:
    """Load and select individual raw execution records."""

    def __init__(self, output_directory: Path) -> None:
        self.output_directory = output_directory
        self.records: list[dict[str, Any]] = []
        self.refresh()

    def refresh(self) -> None:
        raw_directory = self.output_directory / "results" / "raw"
        self.records = []
        for path in sorted(raw_directory.glob("*.json")):
            self.records.append(
                json.loads(path.read_text(encoding="utf-8"))
            )

    def find(
        self,
        *,
        fixture_id: str,
        resolution: str,
        selected_strategy_id: str,
        scenario_id: str,
        repetition: int,
    ) -> dict[str, Any] | None:
        for record in self.records:
            if (
                record.get("fixture_id") == fixture_id
                and record.get("resolution") == resolution
                and record.get("strategy_id") == selected_strategy_id
                and record.get("scenario_id") == scenario_id
                and record.get("repetition") == repetition
            ):
                return record
        return None


def _strategy_spec(selected_strategy_id: str):
    if selected_strategy_id == "crc-only":
        return "crc-only", None
    parts = selected_strategy_id.split("-")
    try:
        rs_marker = parts.index("rs32")
    except ValueError:
        raise ValueError(f"invalid strategy id: {selected_strategy_id}")
    if rs_marker == 0 or len(parts) != rs_marker + 3:
        raise ValueError(f"invalid strategy id: {selected_strategy_id}")
    try:
        data_symbols = int(parts[rs_marker + 1])
        repair_symbols = int(parts[rs_marker + 2])
    except ValueError as error:
        raise ValueError(
            f"invalid strategy id: {selected_strategy_id}"
        ) from error
    strategy = "-".join(parts[:rs_marker])
    if strategy not in ("crc+rs", "rs-only"):
        raise ValueError(f"invalid strategy id: {selected_strategy_id}")
    return strategy, (data_symbols, repair_symbols)


def execute_selected(
    *,
    output_directory: Path,
    source_root: Path,
    fixture_id: str,
    resolution: str,
    selected_strategy_id: str,
    scenario_id: str,
    repetition: int,
) -> dict[str, Any]:
    """Execute one selection from the local viewer."""

    width, height = (int(value) for value in resolution.split("x"))
    strategy, fec_variant = _strategy_spec(selected_strategy_id)
    scenario = next(
        item for item in SCENARIOS if item.scenario_id == scenario_id
    )
    generate_reference_images(
        output_directory / "reference",
        source_root=source_root,
    )
    fixture = build_fixture(
        fixture_id,
        width,
        height,
        source_root=source_root,
    )
    record = execute_one(
        fixture=fixture,
        resolution=(width, height),
        strategy=strategy,
        fec_variant=fec_variant,
        scenario=scenario,
        repetition=repetition,
        output_directory=output_directory,
        source_root=source_root,
    )
    records = write_result_indexes(output_directory)
    write_reports(output_directory, records)
    return record


def _format_state(record: dict[str, Any] | None) -> str:
    if record is None:
        return "SEM RESULTADO — execute o experimento selecionado"
    if record.get("reconstruction_integral"):
        return "RECUPERADA — igual à referência"
    if record.get("reconstruction_available"):
        return "SAÍDA DIVERGENTE — decoder produziu resultado não verificável"
    return f"FALHA — {record.get('failure_reason') or 'sem reconstrução'}"


def _html_document(records: list[dict[str, Any]]) -> str:
    """Build the dependency-free browser viewer."""

    serialized = json.dumps(records, separators=(",", ":")).replace(
        "<",
        "\\u003c",
    )
    fixture_options = "".join(
        f'<option value="{html.escape(value)}">{html.escape(value)}</option>'
        for value in FIXTURE_IDS
    )
    resolution_options = "".join(
        f'<option value="{html.escape(value)}">{html.escape(value)}</option>'
        for value in RESOLUTION_IDS
    )
    strategy_options = "".join(
        f'<option value="{html.escape(value)}">{html.escape(value)}</option>'
        for value in STRATEGY_IDS
    )
    scenario_options = "".join(
        f'<option value="{html.escape(item.scenario_id)}">'
        f'{html.escape(item.scenario_id)}</option>'
        for item in SCENARIOS
    )
    repetition_options = "".join(
        f'<option value="{index}">{index}</option>'
        for index in range(1, 11)
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>MeshMedia Lab — Issue #24</title>
<style>
body {{ background:#f3f4f6; color:#111827; font:14px sans-serif; margin:0; }}
header, main {{ max-width:1120px; margin:auto; padding:16px; }}
header {{ background:#111827; color:white; max-width:none; }}
.controls, .panels, .result {{ display:flex; gap:12px; flex-wrap:wrap; }}
label {{ display:flex; flex-direction:column; gap:4px; font-weight:600; }}
select, button {{ padding:7px; }}
button {{ cursor:pointer; font-weight:700; }}
.panel {{ background:white; border:1px solid #d1d5db; flex:1; min-width:390px;
  padding:10px; text-align:center; }}
.panel img, .missing {{ width:384px; height:384px; max-width:100%;
  object-fit:contain; image-rendering:pixelated; background:#e5e7eb; }}
.missing {{ align-items:center; display:flex; justify-content:center;
  white-space:pre-line; color:#b91c1c; font-weight:700; margin:auto; }}
.result {{ background:white; border:1px solid #d1d5db; margin-top:12px;
  padding:12px; white-space:pre-wrap; }}
.state {{ font-size:16px; font-weight:700; width:100%; }}
</style>
</head>
<body>
<header><h1>MESHMEDIA LAB</h1><div>EXPERIMENTO DE INTEGRIDADE E FEC — Issue #24</div></header>
<main>
<section class="controls">
<label>Fixture<select id="fixture">{fixture_options}</select></label>
<label>Resolução<select id="resolution">{resolution_options}</select></label>
<label>Estratégia<select id="strategy">{strategy_options}</select></label>
<label>Cenário<select id="scenario">{scenario_options}</select></label>
<label>Repetição<select id="repetition">{repetition_options}</select></label>
<button id="execute">EXECUTAR EXPERIMENTO</button>
</section>
<section class="panels">
<div class="panel"><h2>IMAGEM ORIGINAL</h2><img id="original" alt="Imagem original"></div>
<div class="panel"><h2>IMAGEM RECEBIDA</h2><div id="received-missing" class="missing">RECONSTRUÇÃO
NÃO DISPONÍVEL</div><img id="received" alt="Imagem reconstruída" hidden></div>
</section>
<section class="result"><div id="state" class="state"></div><div id="metrics"></div></section>
</main>
<script>
const records = {serialized};
const ids = ["fixture", "resolution", "strategy", "scenario", "repetition"];
const byId = id => document.getElementById(id);
const artifact = path => "/artifact/" + path.split("/").map(encodeURIComponent).join("/");
function findRecord() {{
  return records.find(record =>
    record.fixture_id === byId("fixture").value &&
    record.resolution === byId("resolution").value &&
    record.strategy_id === byId("strategy").value &&
    record.scenario_id === byId("scenario").value &&
    record.repetition === Number(byId("repetition").value));
}}
function render() {{
  const record = findRecord();
  if (!record) {{
    byId("state").textContent = "SEM RESULTADO — execute a célula selecionada";
    byId("metrics").textContent = "";
    byId("received").hidden = true;
    byId("received-missing").hidden = false;
    return;
  }}
  byId("original").src = artifact(record.reference_path);
  const received = byId("received");
  const missing = byId("received-missing");
  if (record.received_image_path) {{
    received.src = artifact(record.received_image_path);
    received.hidden = false;
    missing.hidden = true;
  }} else {{
    received.hidden = true;
    missing.hidden = false;
  }}
  const quality = record.quality || {{}};
  const state = record.reconstruction_integral
    ? "RECUPERADA — igual à referência"
    : record.reconstruction_available
      ? "SAÍDA DIVERGENTE — decoder não verificável"
      : "FALHA — " + (record.failure_reason || "sem reconstrução");
  byId("state").textContent = state;
  byId("metrics").textContent =
    "Resolução: " + record.resolution + " | Estratégia: " + record.strategy_id +
    " | Cenário: " + record.scenario_id + "\\n" +
    "Mensagens: enviadas=" + record.messages_sent +
    " | recebidas=" + record.messages_received +
    " | necessárias=" + record.messages_used_to_conclude + "\\n" +
    "Bytes: úteis=" + record.encoded_bytes +
    " | transmitidos=" + record.wire_bytes +
    " | overhead=" + Number(record.overhead_percent).toFixed(2) + "%\\n" +
    "Pixels diferentes: " + quality.pixels_different +
    " | PSNR: " + (quality.psnr_infinite ? "∞" : quality.psnr_db);
}}
ids.forEach(id => byId(id).addEventListener("change", render));
byId("execute").addEventListener("click", async () => {{
  byId("state").textContent = "EXECUTANDO...";
  const payload = Object.fromEntries(ids.map(id => [id, byId(id).value]));
  const response = await fetch("/api/run", {{
    method:"POST", headers:{{"Content-Type":"application/json"}},
    body:JSON.stringify(payload)
  }});
  const record = await response.json();
  const index = records.findIndex(item => item.run_id === record.run_id);
  if (index >= 0) records[index] = record; else records.push(record);
  render();
}});
render();
</script>
</body>
</html>
"""


def _web_main(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(
        description="Viewer web local da Issue #24",
    )
    parser.add_argument(
        "--results-dir",
        default="experiments/issue-24",
        help="diretório de artefatos do experimento",
    )
    parser.add_argument(
        "--source-root",
        default=".",
        help="raiz do repositório contendo test-images/",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--mode",
        choices=("auto", "web", "tk"),
        default="web",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)
    output_directory = Path(args.results_dir).resolve()
    source_root = Path(args.source_root).resolve()
    catalog = ResultCatalog(output_directory)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send(
                    _html_document(catalog.records).encode("utf-8"),
                    "text/html; charset=utf-8",
                )
                return
            if parsed.path.startswith("/artifact/"):
                relative = unquote(parsed.path[len("/artifact/") :])
                root = output_directory
                candidate = (root / relative).resolve()
                if root not in candidate.parents and candidate != root:
                    self.send_error(403)
                    return
                if not candidate.is_file():
                    self.send_error(404)
                    return
                content_type = mimetypes.guess_type(candidate.name)[0]
                self._send(
                    candidate.read_bytes(),
                    content_type or "application/octet-stream",
                )
                return
            self.send_error(404)

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/run":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            try:
                record = execute_selected(
                    output_directory=output_directory,
                    source_root=source_root,
                    fixture_id=payload["fixture"],
                    resolution=payload["resolution"],
                    selected_strategy_id=payload["strategy"],
                    scenario_id=payload["scenario"],
                    repetition=int(payload["repetition"]),
                )
                catalog.refresh()
            except (KeyError, ValueError, OSError) as error:
                self.send_error(400, str(error))
                return
            self._send(
                json.dumps(record).encode("utf-8"),
                "application/json; charset=utf-8",
            )

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{server.server_address[1]}/"
    print(f"Issue #24 viewer: {url}", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _tk_main(
    argv: list[str] | None = None,
) -> int:
    import tkinter as tk
    from tkinter import ttk

    try:
        from PIL import Image, ImageTk
    except ImportError as error:  # pragma: no cover - local optional extra
        raise SystemExit(
            "Pillow é necessário para o viewer; instale o extra local"
        ) from error

    import argparse

    parser = argparse.ArgumentParser(
        description="Visualizador local da Issue #24",
    )
    parser.add_argument(
        "--results-dir",
        default="experiments/issue-24",
        help="diretório de artefatos do experimento",
    )
    parser.add_argument(
        "--source-root",
        default=".",
        help="raiz do repositório contendo test-images/",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "web", "tk"),
        default="auto",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)
    output_directory = Path(args.results_dir)
    source_root = Path(args.source_root)
    catalog = ResultCatalog(output_directory)

    root = tk.Tk()
    root.title("MeshMedia Lab — Issue #24")
    root.geometry("1100x760")

    fixture_value = tk.StringVar(value=FIXTURE_IDS[0])
    resolution_value = tk.StringVar(value=RESOLUTION_IDS[0])
    strategy_value = tk.StringVar(value=STRATEGY_IDS[0])
    scenario_value = tk.StringVar(value=SCENARIOS[0].scenario_id)
    repetition_value = tk.StringVar(value="1")
    state_value = tk.StringVar(value="")

    controls = ttk.Frame(root, padding=10)
    controls.pack(fill="x")
    selectors = (
        ("Fixture", fixture_value, FIXTURE_IDS),
        ("Resolução", resolution_value, RESOLUTION_IDS),
        ("Estratégia", strategy_value, STRATEGY_IDS),
        (
            "Cenário",
            scenario_value,
            tuple(item.scenario_id for item in SCENARIOS),
        ),
        ("Repetição", repetition_value, tuple(str(i) for i in range(1, 11))),
    )
    for column, (label, variable, values) in enumerate(selectors):
        ttk.Label(controls, text=label).grid(
            row=0,
            column=column,
            padx=4,
            sticky="w",
        )
        ttk.Combobox(
            controls,
            textvariable=variable,
            values=values,
            state="readonly",
            width=18 if label == "Estratégia" else 14,
        ).grid(row=1, column=column, padx=4)

    panels = ttk.Frame(root, padding=10)
    panels.pack(fill="both", expand=True)
    original_frame = ttk.LabelFrame(panels, text="IMAGEM ORIGINAL")
    received_frame = ttk.LabelFrame(panels, text="IMAGEM RECEBIDA")
    original_frame.grid(row=0, column=0, padx=8, sticky="nsew")
    received_frame.grid(row=0, column=1, padx=8, sticky="nsew")
    panels.columnconfigure(0, weight=1)
    panels.columnconfigure(1, weight=1)
    panels.rowconfigure(0, weight=1)
    original_label = ttk.Label(original_frame, anchor="center")
    received_label = ttk.Label(received_frame, anchor="center")
    original_label.pack(fill="both", expand=True)
    received_label.pack(fill="both", expand=True)

    details = ttk.Label(
        root,
        textvariable=state_value,
        padding=10,
        justify="left",
    )
    details.pack(fill="x")

    image_references: dict[str, Any] = {}

    def refresh_view() -> None:
        try:
            repetition = int(repetition_value.get())
        except ValueError:
            repetition = 1
        record = catalog.find(
            fixture_id=fixture_value.get(),
            resolution=resolution_value.get(),
            selected_strategy_id=strategy_value.get(),
            scenario_id=scenario_value.get(),
            repetition=repetition,
        )
        resolution = resolution_value.get()
        reference_path = (
            output_directory
            / "reference"
            / fixture_value.get()
            / f"{resolution}.png"
        )
        if reference_path.exists():
            with Image.open(reference_path) as image:
                original = image.convert("L").resize(
                    (384, 384),
                    _resampling_filter(Image, "NEAREST"),
                )
            image_references["original"] = ImageTk.PhotoImage(original)
            original_label.configure(
                image=image_references["original"],
                text="",
            )
        if record and record.get("received_image_path"):
            received_path = output_directory / record["received_image_path"]
            if received_path.exists():
                with Image.open(received_path) as image:
                    received = image.convert("L").resize(
                        (384, 384),
                        _resampling_filter(Image, "NEAREST"),
                    )
                image_references["received"] = ImageTk.PhotoImage(received)
                received_label.configure(
                    image=image_references["received"],
                    text="",
                )
            else:
                received_label.configure(image="", text="imagem ausente")
        else:
            received_label.configure(
                image="",
                text="RECONSTRUÇÃO\nNÃO DISPONÍVEL",
            )

        if record is None:
            state_value.set(_format_state(None))
            return
        quality = record.get("quality", {})
        state_value.set(
            f"{_format_state(record)}\n"
            f"Resolução: {record.get('resolution')} | "
            f"Estratégia: {record.get('strategy_id')} | "
            f"Cenário: {record.get('scenario_id')}\n"
            f"Mensagens: enviadas={record.get('messages_sent')} | "
            f"recebidas={record.get('messages_received')} | "
            f"necessárias={record.get('messages_used_to_conclude')}\n"
            f"Bytes: úteis={record.get('encoded_bytes')} | "
            f"transmitidos={record.get('wire_bytes')} | "
            f"overhead={record.get('overhead_percent'):.2f}%\n"
            f"Pixels diferentes: {quality.get('pixels_different')} | "
            f"PSNR: {'∞' if quality.get('psnr_infinite') else quality.get('psnr_db')}"
        )

    def execute_view() -> None:
        execute_selected(
            output_directory=output_directory,
            source_root=source_root,
            fixture_id=fixture_value.get(),
            resolution=resolution_value.get(),
            selected_strategy_id=strategy_value.get(),
            scenario_id=scenario_value.get(),
            repetition=int(repetition_value.get()),
        )
        catalog.refresh()
        refresh_view()

    buttons = ttk.Frame(root, padding=10)
    buttons.pack(fill="x")
    ttk.Button(
        buttons,
        text="EXECUTAR EXPERIMENTO",
        command=execute_view,
    ).pack(side="left", padx=4)
    ttk.Button(
        buttons,
        text="ATUALIZAR VISUALIZAÇÃO",
        command=refresh_view,
    ).pack(side="left", padx=4)
    refresh_view()
    root.mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    mode = "auto"
    if "--mode" in values:
        position = values.index("--mode")
        if position + 1 < len(values):
            mode = values[position + 1]
    if mode == "web":
        return _web_main(values)
    if mode == "tk":
        return _tk_main(values)
    try:
        import tkinter
    except ModuleNotFoundError:
        return _web_main(values)
    try:
        return _tk_main(values)
    except tkinter.TclError:
        return _web_main(values)


if __name__ == "__main__":
    raise SystemExit(main())
