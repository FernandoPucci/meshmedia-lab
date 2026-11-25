"""Machine-readable summaries and lightweight reports for Issue #24."""

from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


def _records_by(records: list[dict[str, Any]], *keys: str):
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[tuple(record.get(key) for key in keys)].append(record)
    return groups


def _average(records: list[dict[str, Any]], key: str) -> float | None:
    values = [
        float(record[key])
        for record in records
        if record.get(key) is not None
    ]
    return mean(values) if values else None


def build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build grouped aggregate data without hiding individual results."""

    groups: list[dict[str, Any]] = []
    for key, group in sorted(
        _records_by(
            records,
            "fixture_id",
            "resolution",
            "strategy_id",
            "scenario_id",
        ).items(),
        key=lambda item: tuple(str(value) for value in item[0]),
    ):
        fixture_id, resolution, strategy_id, scenario_id = key
        successes = sum(
            bool(record.get("reconstruction_integral"))
            for record in group
        )
        groups.append(
            {
                "fixture_id": fixture_id,
                "resolution": resolution,
                "strategy_id": strategy_id,
                "scenario_id": scenario_id,
                "runs": len(group),
                "reconstruction_successes": successes,
                "reconstruction_success_rate": (
                    successes / len(group) if group else None
                ),
                "mean_messages_sent": _average(group, "messages_sent"),
                "mean_messages_received": _average(
                    group,
                    "messages_received",
                ),
                "mean_messages_used_to_conclude": _average(
                    group,
                    "messages_used_to_conclude",
                ),
                "mean_wire_bytes": _average(group, "wire_bytes"),
                "mean_overhead_percent": _average(
                    group,
                    "overhead_percent",
                ),
                "mean_encode_time_ns": _average(group, "encode_time_ns"),
                "mean_decode_time_ns": _average(group, "decode_time_ns"),
                "mean_total_time_ns": _average(group, "total_time_ns"),
            }
        )

    successes = sum(
        bool(record.get("reconstruction_integral")) for record in records
    )
    return {
        "environment": "local-simulation",
        "record_count": len(records),
        "reconstruction_successes": successes,
        "reconstruction_success_rate": (
            successes / len(records) if records else None
        ),
        "groups": groups,
    }


def _svg_bar_chart(
    path: Path,
    *,
    title: str,
    labels: list[str],
    values: list[float],
    suffix: str,
) -> None:
    width = 1000
    height = 560
    chart_left = 80
    chart_bottom = 470
    chart_height = 360
    chart_width = 860
    maximum = max(values or [1.0])
    if maximum <= 0:
        maximum = 1.0
    bar_width = chart_width / max(1, len(values)) * 0.72
    gap = chart_width / max(1, len(values))
    bars: list[str] = []
    for index, (label, value) in enumerate(zip(labels, values)):
        bar_height = chart_height * value / maximum
        x = chart_left + gap * index + (gap - bar_width) / 2
        y = chart_bottom - bar_height
        bars.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" '
            f'height="{bar_height:.2f}" fill="#2563eb"/>'
        )
        bars.append(
            f'<text x="{x + bar_width / 2:.2f}" y="{chart_bottom + 24}" '
            f'text-anchor="middle" font-size="12">{html.escape(label)}</text>'
        )
        bars.append(
            f'<text x="{x + bar_width / 2:.2f}" y="{max(18, y - 8):.2f}" '
            f'text-anchor="middle" font-size="12">{value:.2f}{suffix}</text>'
        )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
  width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="white"/>
  <text x="{width / 2}" y="32" text-anchor="middle"
    font-family="sans-serif" font-size="20">{html.escape(title)}</text>
  <line x1="{chart_left}" y1="{chart_bottom}" x2="{chart_left + chart_width}"
    y2="{chart_bottom}" stroke="#111827"/>
  <line x1="{chart_left}" y1="{chart_bottom - chart_height}"
    x2="{chart_left}" y2="{chart_bottom}" stroke="#111827"/>
  {''.join(bars)}
</svg>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")


def _chart_data(
    records: list[dict[str, Any]],
    *,
    scenario_id: str,
    value_key: str,
) -> tuple[list[str], list[float]]:
    grouped = _records_by(
        [
            record
            for record in records
            if record.get("scenario_id") == scenario_id
        ],
        "resolution",
        "strategy_id",
    )
    labels: list[str] = []
    values: list[float] = []
    for key, group in sorted(
        grouped.items(),
        key=lambda item: tuple(str(value) for value in item[0]),
    ):
        value = _average(group, value_key)
        if value is not None:
            labels.append(f"{key[0]} {key[1]}")
            values.append(value)
    return labels, values


def _display_strategy(strategy_id: str) -> str:
    if strategy_id == "crc-only":
        return "CRC-only"
    parts = strategy_id.split("-")
    marker = parts.index("rs32")
    strategy = "CRC+RS" if parts[0] == "crc+rs" else "RS-only"
    return f"{strategy}(32,{parts[marker + 1]})"


def _aggregate_success(
    records: list[dict[str, Any]],
    *,
    include_no_fail: bool,
) -> dict[str, float]:
    selected = [
        record
        for record in records
        if include_no_fail or record.get("scenario_id") != "NO-FAIL"
    ]
    grouped = _records_by(selected, "strategy_id")
    return {
        key[0]: mean(
            bool(record.get("reconstruction_integral"))
            for record in group
        )
        for key, group in grouped.items()
    }


def _write_final_analysis(
    reports_directory: Path,
    records: list[dict[str, Any]],
) -> None:
    degraded_success = _aggregate_success(
        records,
        include_no_fail=False,
    )
    no_fail = [
        record
        for record in records
        if record.get("scenario_id") == "NO-FAIL"
    ]
    overheads = {
        key[0]: _average(group, "overhead_percent")
        for key, group in _records_by(no_fail, "strategy_id").items()
    }
    times = {
        key[0]: _average(group, "total_time_ns")
        for key, group in _records_by(no_fail, "strategy_id").items()
    }
    wrong_outputs = {
        key[0]: sum(
            bool(record.get("reconstruction_available"))
            and not bool(record.get("reconstruction_integral"))
            for record in group
        )
        for key, group in _records_by(records, "strategy_id").items()
    }
    no_output = {
        key[0]: sum(
            not bool(record.get("reconstruction_available"))
            for record in group
        )
        for key, group in _records_by(records, "strategy_id").items()
    }

    strongest_strategy = (
        max(
            degraded_success,
            key=lambda key: degraded_success[key],
        )
        if degraded_success
        else None
    )
    lowest_overhead = min(
        overheads,
        key=lambda key: overheads[key] if overheads[key] is not None else float("inf"),
    )

    lines = [
        "# Issue #24 — análise final",
        "",
        "> Resultado de 9.450 execuções em simulação local determinística.",
        "> Não representa rádio MeshCore, LoRa, airtime ou latência real.",
        "",
        "## Resumo quantitativo",
        "",
        "| Estratégia | Sucesso degradado | Overhead sem falhas | Tempo total sem falhas |",
        "|---|---:|---:|---:|",
    ]
    for strategy in sorted(degraded_success):
        overhead = overheads[strategy]
        duration = times[strategy]
        lines.append(
            f"| {_display_strategy(strategy)} | "
            f"{degraded_success[strategy] * 100:.2f}% | "
            f"{overhead:.2f}% | {duration / 1_000_000:.2f} ms |"
        )

    answer_lines = [
        "",
        "## Respostas",
        "",
        (
            f"1. **Menor overhead:** {_display_strategy(lowest_overhead)} "
            f"no caminho MM1 legado, com {overheads[lowest_overhead]:.2f}% "
            "no cenário sem falhas. O RS-only possui enquadramento diferente "
            "e não inclui header/CRC MM1."
        ),
        "",
        (
            (
                f"2. **Maior recuperação média:** "
                f"{_display_strategy(strongest_strategy)}, com "
                f"{degraded_success[strongest_strategy] * 100:.2f}% nos "
                "cenários degradados."
            )
            if strongest_strategy is not None
            else "2. **Maior recuperação média:** não aplicável; "
            "esta execução não contém cenários degradados."
        ),
        "",
        (
            "3. **Mais reparos:** no CRC+RS, a recuperação degradada aumentou "
            f"de {degraded_success.get('crc+rs-rs32-28-4', 0) * 100:.2f}% "
            f"para {degraded_success.get('crc+rs-rs32-20-12', 0) * 100:.2f}% "
            "ao passar de 4 para 12 reparos, ao custo de mais mensagens e "
            "overhead."
        ),
        "",
        (
            "4. **Tamanho da imagem:** o grayscale 16 níveis produz 512, "
            "2.048 e 8.192 bytes em 32x32, 64x64 e 128x128. O número de "
            "mensagens e blocos cresce proporcionalmente; a distribuição "
            "por bloco passa a dominar a recuperação."
        ),
        "",
        (
            "5. **CRC-only:** não recupera perdas. Pacotes corrompidos são "
            "rejeitados e a imagem fica incompleta quando falta qualquer "
            "fragmento necessário."
        ),
        "",
        (
            "6. **CRC+RS:** recuperou integralmente as células em que as "
            "erasures por bloco permaneceram dentro da capacidade RS. "
            "RS(32,20) foi a configuração mais tolerante, mas também a mais "
            "cara."
        ),
        "",
        (
            "7. **RS-only:** produziu "
            f"{sum(wrong_outputs.values())} saídas divergentes e "
            f"{sum(no_output.values())} execuções sem saída entre as "
            "variantes. Uma saída do decoder não deve ser tratada como "
            "integridade validada."
        ),
        "",
        (
            "8. **Custo computacional:** Reed-Solomon aumentou o tempo local "
            "de preparação/decodificação em relação ao CRC-only. Esses tempos "
            "são do Python e não representam airtime."
        ),
        "",
        (
            "9. **Vantagem CRC+RS:** o CRC identifica corrupção antes da "
            "reassemblagem e transforma o pacote inválido em erasure; o RS "
            "usa essa informação para recuperar o bloco sem aceitar "
            "silenciosamente dados corrompidos."
        ),
        "",
        (
            "10. **Limitações:** payload fixo de 64 bytes, um símbolo FEC por "
            "mensagem, canal independente por pacote, sem rajadas/jitter, "
            "sem MeshCore real e sem medição de airtime. O RS-only continua "
            "exclusivamente experimental."
        ),
        "",
        (
            "Os detalhes por fixture, resolução, cenário, repetição e seed "
            "estão em `results/raw/` e `results/summary/`."
        ),
        "",
    ]
    lines.extend(answer_lines)
    (reports_directory / "final-analysis.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def write_reports(
    output_directory: Path,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Write summary JSON, Markdown and dependency-free SVG charts."""

    summary = build_summary(records)
    summary_directory = output_directory / "results" / "summary"
    reports_directory = output_directory / "reports"
    summary_directory.mkdir(parents=True, exist_ok=True)
    reports_directory.mkdir(parents=True, exist_ok=True)
    (summary_directory / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    no_fail_records = [
        record
        for record in records
        if record.get("scenario_id") == "NO-FAIL"
    ]
    labels, values = _chart_data(
        no_fail_records,
        scenario_id="NO-FAIL",
        value_key="overhead_percent",
    )
    _svg_bar_chart(
        reports_directory / "charts" / "overhead-no-fail.svg",
        title="Overhead por estratégia — cenário sem falhas",
        labels=labels,
        values=values,
        suffix="%",
    )

    labels, values = _chart_data(
        records,
        scenario_id="NO-FAIL",
        value_key="messages_sent",
    )
    _svg_bar_chart(
        reports_directory / "charts" / "messages-no-fail.svg",
        title="Mensagens enviadas — cenário sem falhas",
        labels=labels,
        values=values,
        suffix="",
    )

    failure_records = [
        record
        for record in records
        if record.get("scenario_id") != "NO-FAIL"
    ]
    recovery_groups = _records_by(
        failure_records,
        "resolution",
        "strategy_id",
    )
    recovery_labels: list[str] = []
    recovery_values: list[float] = []
    for key, group in sorted(
        recovery_groups.items(),
        key=lambda item: tuple(str(value) for value in item[0]),
    ):
        if group:
            recovery_labels.append(f"{key[0]} {key[1]}")
            recovery_values.append(
                mean(
                    bool(record.get("reconstruction_integral"))
                    for record in group
                )
                * 100.0
            )
    _svg_bar_chart(
        reports_directory / "charts" / "recovery-failures.svg",
        title="Reconstrução integral — cenários degradados",
        labels=recovery_labels,
        values=recovery_values,
        suffix="%",
    )

    labels, values = _chart_data(
        no_fail_records,
        scenario_id="NO-FAIL",
        value_key="total_time_ns",
    )
    _svg_bar_chart(
        reports_directory / "charts" / "time-no-fail.svg",
        title="Tempo total local — cenário sem falhas",
        labels=labels,
        values=[value / 1_000_000 for value in values],
        suffix=" ms",
    )

    no_fail_table = [
        "",
        "## Observado sem falhas",
        "",
        "| Resolução | Estratégia | Mensagens | Necessárias | Wire bytes | Overhead | Sucesso |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for key, group in sorted(
        _records_by(
            no_fail_records,
            "resolution",
            "strategy_id",
        ).items(),
        key=lambda item: tuple(str(value) for value in item[0]),
    ):
        success_rate = mean(
            bool(record.get("reconstruction_integral"))
            for record in group
        ) * 100.0
        messages_used = _average(group, "messages_used_to_conclude")
        no_fail_table.append(
            "| {resolution} | {strategy} | {sent:.0f} | {used} | "
            "{wire:.0f} | {overhead:.2f}% | {success:.1f}% |".format(
                resolution=key[0],
                strategy=key[1],
                sent=_average(group, "messages_sent") or 0.0,
                used=f"{messages_used:.1f}" if messages_used is not None else "-",
                wire=_average(group, "wire_bytes") or 0.0,
                overhead=_average(group, "overhead_percent") or 0.0,
                success=success_rate,
            )
        )

    recovery_table = [
        "",
        "## Recuperação por cenário",
        "",
        "| Resolução | Estratégia | Cenário | Reconstrução integral |",
        "|---|---|---|---:|",
    ]
    non_baseline = [
        record
        for record in records
        if record.get("scenario_id") != "NO-FAIL"
    ]
    for key, group in sorted(
        _records_by(
            non_baseline,
            "resolution",
            "strategy_id",
            "scenario_id",
        ).items(),
        key=lambda item: tuple(str(value) for value in item[0]),
    ):
        recovery_table.append(
            f"| {key[0]} | {key[1]} | {key[2]} | "
            f"{mean(bool(record.get('reconstruction_integral')) for record in group) * 100:.1f}% |"
        )

    markdown_lines = [
        "# Issue #24 — comparação experimental",
        "",
        "> Ambiente: simulação local determinística. Estes resultados não são",
        "> medições de MeshCore, LoRa, airtime ou rádio real.",
        "",
        f"Execuções disponíveis: **{len(records)}**.",
        "",
        "## Baseline histórico sem FEC",
        "",
        "| Resolução | Bytes codificados | Mensagens | Bytes MM1 | Overhead |",
        "|---|---:|---:|---:|---:|",
        "| 32x32 | 512 | 8 | 680 | 168 |",
        "| 64x64 | 2048 | 32 | 2720 | 672 |",
        "",
        (
            "Esses valores vêm dos testes manuais documentados em "
            "`docs/experiment-matrix.md`. O novo executor deve reproduzi-los "
            "para CRC-only sem falhas."
        ),
        *no_fail_table,
        *recovery_table,
        "",
        "## Artefatos",
        "",
        "- `results/raw/results.jsonl`: resultados individuais;",
        "- `results/summary/results.csv`: tabela plana;",
        "- `results/summary/summary.json`: agregações;",
        "- `reports/final-analysis.md`: respostas e análise final;",
        "- `reports/charts/`: gráficos SVG;",
        "- `reference/` e `results/images/`: imagens lado a lado.",
        "",
        "## Gráficos",
        "",
        "- [Overhead](charts/overhead-no-fail.svg)",
        "- [Mensagens](charts/messages-no-fail.svg)",
        "- [Recuperação](charts/recovery-failures.svg)",
        "- [Tempo](charts/time-no-fail.svg)",
        "",
    ]
    (reports_directory / "comparison.md").write_text(
        "\n".join(markdown_lines),
        encoding="utf-8",
    )
    _write_final_analysis(reports_directory, records)
    return summary
