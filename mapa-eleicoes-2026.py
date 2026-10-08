from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import pandas as pd


MAP_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty"
MAP_ATTRIBUTION = (
    '<a href="https://openfreemap.org/">OpenFreeMap</a> '
    '© <a href="https://www.openmaptiles.org/">OpenMapTiles</a> '
    'Data from <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
)
CHAVES_LOCAL = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO"]
METRICAS_ELEITORADO = ["QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES"]
CATEGORIAS_PRESIDENTE = [
    "VALIDO_NOMINAL",
    "VALIDO_LEGENDA",
    "BRANCO",
    "NULO",
]


def texto(valor: object) -> str:
    return "" if pd.isna(valor) else str(valor)


def escapar(valor: object) -> str:
    return html.escape(texto(valor))


def inteiro(valor: object) -> int:
    convertido = pd.to_numeric(valor, errors="coerce")
    return 0 if pd.isna(convertido) else int(convertido)


def percentual(valor: int, total: int) -> str:
    if not total:
        return "0,0%"
    return f"{100 * valor / total:.1f}%".replace(".", ",")


def chave_local(row: pd.Series | dict[str, object]) -> tuple[str, ...]:
    return tuple(texto(row.get(coluna, "")).strip() for coluna in CHAVES_LOCAL)


def carregar_presidente(caminho: Path) -> dict[tuple[str, ...], list[dict[str, object]]]:
    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo presidencial não encontrado: {caminho}. "
            "Reprocesse os dados com a versão atualizada do pipeline."
        )

    dados = pd.read_csv(
        caminho,
        sep=";",
        dtype={
            "SG_UF": "string",
            "CD_MUNICIPIO": "string",
            "NR_ZONA": "string",
            "NR_LOCAL_VOTACAO": "string",
            "CATEGORIA_VOTO": "string",
            "CANDIDATO_OU_LEGENDA": "string",
        },
        keep_default_na=False,
        encoding="utf-8-sig",
    )
    obrigatorias = set(CHAVES_LOCAL + ["CATEGORIA_VOTO", "CANDIDATO_OU_LEGENDA", "QT_VOTOS"])
    faltantes = obrigatorias - set(dados.columns)
    if faltantes:
        raise ValueError(
            "O arquivo presidencial não possui as colunas: "
            + ", ".join(sorted(faltantes))
        )

    dados["QT_VOTOS"] = pd.to_numeric(dados["QT_VOTOS"], errors="coerce").fillna(0).astype(int)
    resultado: dict[tuple[str, ...], list[dict[str, object]]] = {}
    for chave, grupo in dados.groupby(CHAVES_LOCAL, dropna=False, observed=True):
        if not isinstance(chave, tuple):
            chave = (chave,)
        resultado[tuple(texto(valor).strip() for valor in chave)] = grupo.to_dict("records")
    return resultado


def html_presidente(registros: list[dict[str, object]]) -> str:
    totais = {categoria: 0 for categoria in CATEGORIAS_PRESIDENTE}
    for registro in registros:
        categoria = texto(registro.get("CATEGORIA_VOTO"))
        if categoria in totais:
            totais[categoria] += inteiro(registro.get("QT_VOTOS"))

    validos = totais["VALIDO_NOMINAL"] + totais["VALIDO_LEGENDA"]
    total_votos = sum(totais.values())
    linhas: list[str] = []

    candidatos = [
        registro
        for registro in registros
        if texto(registro.get("CATEGORIA_VOTO"))
        in {"VALIDO_NOMINAL", "VALIDO_LEGENDA"}
        and inteiro(registro.get("QT_VOTOS")) > 0
    ]
    candidatos.sort(key=lambda registro: inteiro(registro.get("QT_VOTOS")), reverse=True)
    for registro in candidatos:
        votos = inteiro(registro.get("QT_VOTOS"))
        nome = texto(registro.get("CANDIDATO_OU_LEGENDA")) or texto(
            registro.get("NM_VOTAVEL")
        )
        linhas.append(
            f'<div class="candidato"><b>{escapar(nome)}</b>: '
            f'<strong>{votos:,}</strong> voto(s) — '
            f'{percentual(votos, validos)} dos válidos; '
            f'{percentual(votos, total_votos)} do total</div>'
        )

    if not linhas:
        linhas.append("<div>Não foram encontrados votos presidenciais para este local.</div>")

    linhas.extend(
        [
            f'<div class="categoria"><b>Votos válidos:</b> {validos:,} '
            f'({percentual(validos, total_votos)} do total)</div>',
            f'<div class="categoria"><b>Votos brancos:</b> {totais["BRANCO"]:,} '
            f'({percentual(totais["BRANCO"], total_votos)} do total)</div>',
            f'<div class="categoria nulo"><b>Votos nulos:</b> {totais["NULO"]:,} '
            f'({percentual(totais["NULO"], total_votos)} do total)</div>',
        ]
    )
    return "".join(linhas)


def construir_popup(row: pd.Series, registros: list[dict[str, object]]) -> str:
    aptos = inteiro(row.get("QT_APTOS"))
    comparecimento = inteiro(row.get("QT_COMPARECIMENTO"))
    abstencoes = inteiro(row.get("QT_ABSTENCOES"))
    nome_local = texto(row.get("NM_LOCAL_VOTACAO")) or "Local não informado"
    endereco = texto(row.get("DS_ENDERECO")) or "Endereço não informado"
    bairro = texto(row.get("DS_BAIRRO"))
    cep = texto(row.get("NR_CEP"))
    cidade = texto(row.get("NM_MUNICIPIO"))
    zona = texto(row.get("NR_ZONA"))
    local_codigo = texto(row.get("NR_LOCAL_VOTACAO"))
    presidencia = html_presidente(registros)
    total_presidente = sum(
        inteiro(registro.get("QT_VOTOS")) for registro in registros
    )

    return f"""
    <div class="popup">
      <h3>{escapar(nome_local)}</h3>
      <div><b>Município:</b> {escapar(cidade)}</div>
      <div><b>Zona eleitoral:</b> {escapar(zona)}</div>
      <div><b>Código do local:</b> {escapar(local_codigo)}</div>
      <hr>
      <h4>Eleitorado e participação</h4>
      <div><b>Eleitores aptos:</b> {aptos:,}</div>
      <div><b>Compareceram:</b> {comparecimento:,} ({percentual(comparecimento, aptos)} dos aptos)</div>
      <div class="abstencao"><b>Não votaram / abstenções:</b> {abstencoes:,} ({percentual(abstencoes, aptos)} dos aptos)</div>
      <hr>
      <h4>Presidência</h4>
      <div><b>Votos apurados:</b> {total_presidente:,}</div>
      {presidencia}
      <div class="endereco-final"><b>Endereço da urna/local:</b><br>
        {escapar(endereco)}{(' — ' + escapar(bairro)) if bairro else ''}{(' — CEP ' + escapar(cep)) if cep else ''}
      </div>
    </div>
    """


def criar_mapa(entrada: Path, presidente_path: Path, saida: Path) -> None:
    dados = pd.read_csv(
        entrada,
        sep=";",
        dtype={
            "SG_UF": "string",
            "CD_MUNICIPIO": "string",
            "NR_ZONA": "string",
            "NR_LOCAL_VOTACAO": "string",
        },
        keep_default_na=False,
        encoding="utf-8-sig",
    )
    obrigatorias = set(
        CHAVES_LOCAL
        + [
            "NM_MUNICIPIO",
            "NM_LOCAL_VOTACAO",
            "DS_ENDERECO",
            "DS_BAIRRO",
            "NR_CEP",
            "VL_LATITUDE",
            "VL_LONGITUDE",
            "TOTAL_VOTOS",
            *METRICAS_ELEITORADO,
        ]
    )
    faltantes = obrigatorias - set(dados.columns)
    if faltantes:
        raise ValueError(
            "O arquivo de totais por local não possui as colunas necessárias: "
            + ", ".join(sorted(faltantes))
            + ". Reprocesse o BU com a versão atualizada do pipeline."
        )

    for coluna in ["VL_LATITUDE", "VL_LONGITUDE", *METRICAS_ELEITORADO]:
        dados[coluna] = pd.to_numeric(dados[coluna], errors="coerce")
    dados = dados.dropna(subset=["VL_LATITUDE", "VL_LONGITUDE"]).copy()
    if dados.empty:
        raise ValueError("Nenhuma coordenada foi encontrada nos totais por local.")

    presidente = carregar_presidente(presidente_path)
    features = []
    for _, row in dados.iterrows():
        lat = float(row["VL_LATITUDE"])
        lon = float(row["VL_LONGITUDE"])
        registros = presidente.get(chave_local(row), [])
        popup = construir_popup(row, registros)
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "nome": texto(row.get("NM_LOCAL_VOTACAO")),
                    "zona": texto(row.get("NR_ZONA")),
                    "local": texto(row.get("NR_LOCAL_VOTACAO")),
                    "popup_html": popup,
                },
            }
        )

    geojson = {"type": "FeatureCollection", "features": features}
    geojson_text = json.dumps(geojson, ensure_ascii=False).replace("</", "<\\/")
    bounds = [
        [float(dados["VL_LONGITUDE"].min()), float(dados["VL_LATITUDE"].min())],
        [float(dados["VL_LONGITUDE"].max()), float(dados["VL_LATITUDE"].max())],
    ]
    centro = [float(dados["VL_LONGITUDE"].mean()), float(dados["VL_LATITUDE"].mean())]

    html_documento = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Resultado das Eleições 2026 — Presidência — Distrito Federal</title>
  <link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
  <style>
    html, body, #map {{ height: 100%; margin: 0; }}
    body {{ font-family: Arial, sans-serif; }}
    .cabecalho {{ position: absolute; z-index: 2; top: 12px; left: 12px; max-width: 420px; padding: 12px 15px; border-radius: 8px; background: rgba(255,255,255,.95); box-shadow: 0 1px 5px rgba(0,0,0,.25); }}
    .cabecalho h1 {{ margin: 0 0 5px; font-size: 17px; }}
    .cabecalho p {{ margin: 0; font-size: 12px; line-height: 1.35; }}
    .fonte {{ position: absolute; z-index: 2; bottom: 6px; left: 6px; padding: 3px 6px; font-size: 11px; background: rgba(255,255,255,.9); }}
    .popup {{ min-width: 300px; max-width: 390px; font-size: 12px; line-height: 1.35; }}
    .popup h3 {{ margin: 0 0 7px; font-size: 16px; color: #1647b7; }}
    .popup h4 {{ margin: 9px 0 4px; font-size: 13px; }}
    .popup hr {{ border: 0; border-top: 1px solid #ddd; margin: 8px 0; }}
    .candidato {{ margin: 3px 0; }}
    .categoria {{ margin-top: 4px; }}
    .nulo {{ color: #9a1b1b; }}
    .abstencao {{ color: #784900; margin-top: 3px; }}
    .endereco-final {{ margin-top: 10px; padding: 8px; border-left: 4px solid #1647b7; background: #eef4ff; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="cabecalho">
    <h1>Presidência — Eleições 2026 — Distrito Federal</h1>
    <p>Clique em um ponto para ver votos por candidato, válidos, brancos, nulos, abstenções e o endereço da urna/local.</p>
  </div>
  <div class="fonte">{MAP_ATTRIBUTION}</div>
  <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
  <script>
    const locais = {geojson_text};
    const centro = {json.dumps(centro)};
    const limites = {json.dumps(bounds)};
    const mapa = new maplibregl.Map({{
      container: 'map',
      style: {json.dumps(MAP_STYLE_URL)},
      center: centro,
      zoom: 10
    }});
    mapa.addControl(new maplibregl.NavigationControl(), 'top-right');
    mapa.addControl(new maplibregl.AttributionControl({{compact: false, customAttribution: {json.dumps(MAP_ATTRIBUTION)}}}));
    mapa.on('load', () => {{
      mapa.addSource('locais', {{ type: 'geojson', data: locais }});
      mapa.addLayer({{
        id: 'locais-pontos',
        type: 'circle',
        source: 'locais',
        paint: {{
          'circle-radius': 6,
          'circle-color': '#155eef',
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 1.5,
          'circle-opacity': 0.85
        }}
      }});
      mapa.fitBounds(limites, {{ padding: 55, maxZoom: 11 }});
    }});
    mapa.on('click', 'locais-pontos', (evento) => {{
      const ponto = evento.features[0];
      new maplibregl.Popup({{ maxWidth: '420px' }})
        .setLngLat(ponto.geometry.coordinates)
        .setHTML(ponto.properties.popup_html)
        .addTo(mapa);
    }});
    mapa.on('mouseenter', 'locais-pontos', () => {{ mapa.getCanvas().style.cursor = 'pointer'; }});
    mapa.on('mouseleave', 'locais-pontos', () => {{ mapa.getCanvas().style.cursor = ''; }});
  </script>
</body>
</html>
"""
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(html_documento, encoding="utf-8")
    print(f"Mapa gerado com {len(features):,} locais: {saida.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera mapa presidencial detalhado dos locais de votação do DF."
    )
    parser.add_argument(
        "--entrada",
        type=Path,
        default=Path("outputs/totais_por_local.csv"),
        help="CSV de totais por local gerado pelo pipeline.",
    )
    parser.add_argument(
        "--presidente",
        type=Path,
        default=None,
        help="CSV presidencial; por padrão, fica na mesma pasta de --entrada.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path("outputs/mapa_eleicoes_df.html"),
        help="HTML do mapa interativo.",
    )
    args = parser.parse_args()
    presidente = args.presidente or args.entrada.parent / "votos_presidente_por_local.csv"
    criar_mapa(args.entrada, presidente, args.saida)


if __name__ == "__main__":
    main()
