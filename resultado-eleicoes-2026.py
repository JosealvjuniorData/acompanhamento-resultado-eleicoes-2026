from __future__ import annotations

import argparse
import hashlib
import sys
import time
import zipfile
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


# Eleições Gerais de 2026 — 1º turno — Distrito Federal
UF = "DF"
PLEITO = "3220"
CD_ELEICAO_ESTADUAL = "6259"
TURNO = "1"

# Fonte oficial publicada pelo TSE em 06/10/2026.
URL_BU_DF = (
    "https://cdn.tse.jus.br/estatistica/sead/eleicoes/"
    "eleicoes2026/buweb/bweb_1t_DF_051020261403.zip"
)
URL_DATASET_TSE = "https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna"
URL_LOCALIZACOES_TSE = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/"
    "eleitorado_locais_votacao/eleitorado_local_votacao_2026.zip"
)

CATEGORIAS_VOTO = [
    "VALIDO_NOMINAL",
    "VALIDO_LEGENDA",
    "BRANCO",
    "NULO",
]

COLUNAS_ORIGINAIS_OBRIGATORIAS = [
    "SG_UF",
    "CD_MUNICIPIO",
    "NM_MUNICIPIO",
    "NR_ZONA",
    "NR_SECAO",
    "NR_LOCAL_VOTACAO",
    "CD_CARGO_PERGUNTA",
    "DS_CARGO_PERGUNTA",
    "NR_PARTIDO",
    "SG_PARTIDO",
    "NM_PARTIDO",
    "CD_TIPO_VOTAVEL",
    "DS_TIPO_VOTAVEL",
    "NR_VOTAVEL",
    "NM_VOTAVEL",
    "QT_VOTOS",
    "NR_URNA_EFETIVADA",
    "DS_TIPO_URNA",
    "QT_APTOS",
    "QT_COMPARECIMENTO",
    "QT_ABSTENCOES",
    "DT_BU_RECEBIDO",
    "DT_ABERTURA",
    "DT_ENCERRAMENTO",
    "DT_EMISSAO_BU",
    "DS_SECOES_AGREGADAS",
]

COLUNAS_LOCALIZACAO = [
    "NM_LOCAL_VOTACAO",
    "DS_ENDERECO",
    "DS_BAIRRO",
    "NR_CEP",
    "VL_LATITUDE",
    "VL_LONGITUDE",
    "FONTE_LOCALIZACAO",
]

COLUNAS_SAIDA = [
    "SG_UF",
    "CD_MUNICIPIO",
    "NM_MUNICIPIO",
    "NR_ZONA",
    "NR_SECAO",
    "NR_LOCAL_VOTACAO",
    "NR_URNA_EFETIVADA",
    *COLUNAS_LOCALIZACAO,
    "DS_CARGO_PERGUNTA",
    "CD_CARGO_PERGUNTA",
    "CATEGORIA_VOTO",
    "MOTIVO_ORIGEM",
    "NR_PARTIDO",
    "SG_PARTIDO",
    "NM_PARTIDO",
    "NR_VOTAVEL",
    "NM_VOTAVEL",
    "CANDIDATO_OU_LEGENDA",
    "QT_VOTOS",
    "QT_APTOS",
    "QT_COMPARECIMENTO",
    "QT_ABSTENCOES",
    "DS_TIPO_URNA",
    "DT_BU_RECEBIDO",
    "DT_ABERTURA",
    "DT_ENCERRAMENTO",
    "DT_EMISSAO_BU",
    "DS_SECOES_AGREGADAS",
]

COLUNAS_AGREGACAO = [
    "SG_UF",
    "CD_MUNICIPIO",
    "NM_MUNICIPIO",
    "NR_ZONA",
    "NR_SECAO",
    "NR_LOCAL_VOTACAO",
    "NR_URNA_EFETIVADA",
    *COLUNAS_LOCALIZACAO,
    "DS_CARGO_PERGUNTA",
    "CD_CARGO_PERGUNTA",
    "CATEGORIA_VOTO",
    "MOTIVO_ORIGEM",
    "NR_PARTIDO",
    "SG_PARTIDO",
    "NM_PARTIDO",
    "NR_VOTAVEL",
    "NM_VOTAVEL",
    "CANDIDATO_OU_LEGENDA",
]


METRICAS_ELEITORADO = ["QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES"]


MOTIVOS_VOTO = {
    "Nominal": (
        "Válido nominal: voto atribuído ao candidato identificado pela urna."
    ),
    "Legenda": (
        "Válido de legenda: voto atribuído ao partido/legenda identificado pela urna."
    ),
    "Branco": "Branco: registro oficial de voto em branco.",
    "Nulo": (
        "Nulo: classificação oficial do BU; a causa específica da nulidade "
        "não é publicada no BU/CSV do TSE."
    ),
}


def normalizar_codigo(serie: pd.Series, largura: int) -> pd.Series:
    """Preserva códigos como texto e completa zeros à esquerda quando possível."""
    texto = serie.astype("string").fillna("").str.strip()
    preenchido = texto.ne("")
    convertido = pd.to_numeric(texto.where(preenchido), errors="coerce")
    resultado = texto.copy()
    resultado.loc[convertido.notna()] = (
        convertido.loc[convertido.notna()].astype("Int64").astype("string").str.zfill(largura)
    )
    return resultado


def garantir_pasta(caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)


def sha512(caminho: Path) -> str:
    digest = hashlib.sha512()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def baixar_arquivo(url: str, destino: Path) -> Path:
    """Baixa o ZIP com arquivo temporário para evitar deixar download parcial."""
    garantir_pasta(destino)
    parcial = destino.with_suffix(destino.suffix + ".part")
    print(f"Baixando fonte oficial do TSE: {url}")

    inicio = time.monotonic()
    with requests.get(
        url,
        stream=True,
        timeout=(30, 180),
        headers={"User-Agent": "acompanhamento-resultado-eleicoes-2026/1.0"},
    ) as resposta:
        resposta.raise_for_status()
        total = int(resposta.headers.get("content-length", "0"))
        recebido = 0
        with parcial.open("wb") as arquivo:
            for bloco in resposta.iter_content(chunk_size=1024 * 1024):
                if not bloco:
                    continue
                arquivo.write(bloco)
                recebido += len(bloco)
                if total:
                    percentual = recebido / total * 100
                    print(
                        f"\r  {percentual:6.2f}% — "
                        f"{recebido / 1024 / 1024:,.1f} / {total / 1024 / 1024:,.1f} MB",
                        end="",
                        flush=True,
                    )
    parcial.replace(destino)
    print(f"\nDownload concluído em {time.monotonic() - inicio:.1f}s.")
    print(f"SHA-512: {sha512(destino)}")
    return destino


def extrair_csv(zip_path: Path, destino: Path) -> Path:
    """Extrai o CSV do ZIP oficial e retorna o caminho do arquivo."""
    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as arquivo_zip:
        csvs = [nome for nome in arquivo_zip.namelist() if nome.lower().endswith(".csv")]
        if not csvs:
            raise FileNotFoundError("O ZIP não contém um arquivo CSV.")
        nome_csv = csvs[0]
        caminho_csv = destino / Path(nome_csv).name
        if not caminho_csv.exists() or caminho_csv.stat().st_size == 0:
            print(f"Extraindo {nome_csv}...")
            with arquivo_zip.open(nome_csv) as origem, caminho_csv.open("wb") as destino_csv:
                while bloco := origem.read(1024 * 1024):
                    destino_csv.write(bloco)
        return caminho_csv


def extrair_csv_localizacoes_tse(zip_path: Path, destino: Path) -> Path:
    """Extrai somente o CSV do Distrito Federal da base oficial de locais."""
    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as arquivo_zip:
        candidatos = [
            nome
            for nome in arquivo_zip.namelist()
            if nome.upper().endswith(f"_{UF}.CSV")
        ]
        if not candidatos:
            raise FileNotFoundError(
                f"O ZIP de locais não contém o arquivo da UF {UF}."
            )
        nome_csv = candidatos[0]
        caminho_csv = destino / Path(nome_csv).name
        if not caminho_csv.exists() or caminho_csv.stat().st_size == 0:
            print(f"Extraindo localização oficial: {nome_csv}...")
            with arquivo_zip.open(nome_csv) as origem, caminho_csv.open("wb") as destino_csv:
                while bloco := origem.read(1024 * 1024):
                    destino_csv.write(bloco)
        return caminho_csv


def criar_modelo_localizacao(caminho: Path) -> None:
    """Cria o modelo de vinculação do código do local ao endereço físico."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    cabecalho = [
        "SG_UF",
        "CD_MUNICIPIO",
        "NR_ZONA",
        "NR_LOCAL_VOTACAO",
        "NM_LOCAL_VOTACAO",
        "DS_ENDERECO",
        "DS_BAIRRO",
        "NR_CEP",
        "VL_LATITUDE",
        "VL_LONGITUDE",
        "FONTE_LOCALIZACAO",
    ]
    pd.DataFrame(columns=cabecalho).to_csv(
        caminho, sep=";", index=False, encoding="utf-8-sig"
    )
    print(f"Modelo criado em: {caminho}")


def gerar_localizacoes_tse(csv_path: Path, saida: Path) -> Path:
    """Converte a base oficial de locais do TSE para o leiaute do projeto."""
    bruto = pd.read_csv(
        csv_path,
        sep=";",
        encoding="latin1",
        dtype="string",
        keep_default_na=False,
    )
    obrigatorias = {
        "SG_UF",
        "CD_MUNICIPIO",
        "NR_ZONA",
        "NR_LOCAL_VOTACAO",
        "NM_LOCAL_VOTACAO",
        "DS_ENDERECO",
        "NM_BAIRRO",
        "NR_CEP",
        "NR_LATITUDE",
        "NR_LONGITUDE",
    }
    faltantes = obrigatorias - set(bruto.columns)
    if faltantes:
        raise ValueError(
            "A base de locais do TSE não possui as colunas: "
            + ", ".join(sorted(faltantes))
        )

    bruto = bruto[bruto["SG_UF"].str.upper().eq(UF)].copy()
    locais = pd.DataFrame(
        {
            "SG_UF": bruto["SG_UF"].str.upper().str.strip(),
            "CD_MUNICIPIO": normalizar_codigo(bruto["CD_MUNICIPIO"], 5),
            "NR_ZONA": normalizar_codigo(bruto["NR_ZONA"], 1),
            "NR_LOCAL_VOTACAO": normalizar_codigo(bruto["NR_LOCAL_VOTACAO"], 4),
            "NM_LOCAL_VOTACAO": bruto["NM_LOCAL_VOTACAO"].str.strip(),
            "DS_ENDERECO": bruto["DS_ENDERECO"].str.strip(),
            "DS_BAIRRO": bruto["NM_BAIRRO"].str.strip(),
            "NR_CEP": bruto["NR_CEP"].str.strip(),
            "VL_LATITUDE": pd.to_numeric(
                bruto["NR_LATITUDE"].str.replace(",", ".", regex=False),
                errors="coerce",
            ),
            "VL_LONGITUDE": pd.to_numeric(
                bruto["NR_LONGITUDE"].str.replace(",", ".", regex=False),
                errors="coerce",
            ),
            "FONTE_LOCALIZACAO": URL_LOCALIZACOES_TSE,
        }
    )
    chaves = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO"]
    locais = locais.drop_duplicates(chaves)
    if locais.empty:
        raise RuntimeError(f"Nenhum local da UF {UF} foi encontrado na base do TSE.")
    saida.parent.mkdir(parents=True, exist_ok=True)
    locais.to_csv(saida, sep=";", index=False, encoding="utf-8-sig")
    print(f"Localizações oficiais do TSE gravadas em: {saida}")
    print(f"Locais distintos vinculados: {len(locais):,}")
    return saida


def carregar_localizacoes(caminho: Path | None) -> pd.DataFrame | None:
    if caminho is None:
        return None
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de localizações não encontrado: {caminho}")

    locais = pd.read_csv(
        caminho,
        sep=";",
        dtype="string",
        keep_default_na=False,
        encoding="utf-8-sig",
    )
    obrigatorias = {"SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO"}
    faltantes = obrigatorias - set(locais.columns)
    if faltantes:
        raise ValueError(
            "O arquivo de localizações não contém as colunas obrigatórias: "
            + ", ".join(sorted(faltantes))
        )

    for coluna in COLUNAS_LOCALIZACAO:
        if coluna not in locais.columns:
            locais[coluna] = ""

    locais["SG_UF"] = locais["SG_UF"].str.upper().str.strip()
    locais["CD_MUNICIPIO"] = normalizar_codigo(locais["CD_MUNICIPIO"], 5)
    locais["NR_ZONA"] = normalizar_codigo(locais["NR_ZONA"], 1)
    locais["NR_LOCAL_VOTACAO"] = normalizar_codigo(locais["NR_LOCAL_VOTACAO"], 4)
    for coluna in ["VL_LATITUDE", "VL_LONGITUDE"]:
        locais[coluna] = pd.to_numeric(locais[coluna], errors="coerce")

    chaves = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO"]
    return locais[chaves + COLUNAS_LOCALIZACAO].drop_duplicates(chaves)


def normalizar_chunk(chunk: pd.DataFrame, locais: pd.DataFrame | None) -> pd.DataFrame:
    faltantes = set(COLUNAS_ORIGINAIS_OBRIGATORIAS) - set(chunk.columns)
    if faltantes:
        raise ValueError(
            "O CSV não possui as colunas esperadas: " + ", ".join(sorted(faltantes))
        )

    chunk = chunk[chunk["SG_UF"].astype("string").str.upper().eq(UF)].copy()
    if chunk.empty:
        return chunk

    for coluna in COLUNAS_ORIGINAIS_OBRIGATORIAS:
        if chunk[coluna].dtype != "string":
            chunk[coluna] = chunk[coluna].astype("string")
        chunk[coluna] = chunk[coluna].fillna("").str.strip()

    chunk["SG_UF"] = chunk["SG_UF"].str.upper()
    chunk["CD_MUNICIPIO"] = normalizar_codigo(chunk["CD_MUNICIPIO"], 5)
    chunk["NR_ZONA"] = normalizar_codigo(chunk["NR_ZONA"], 1)
    chunk["NR_LOCAL_VOTACAO"] = normalizar_codigo(chunk["NR_LOCAL_VOTACAO"], 4)
    chunk["QT_VOTOS"] = pd.to_numeric(chunk["QT_VOTOS"], errors="coerce").fillna(0).astype("int64")

    tipo = chunk["DS_TIPO_VOTAVEL"]
    chunk["CATEGORIA_VOTO"] = tipo.map(
        {
            "Nominal": "VALIDO_NOMINAL",
            "Legenda": "VALIDO_LEGENDA",
            "Branco": "BRANCO",
            "Nulo": "NULO",
        }
    ).fillna("OUTRO")
    chunk["MOTIVO_ORIGEM"] = tipo.map(MOTIVOS_VOTO).fillna(
        "Tipo de voto não previsto no leiaute consultado."
    )
    chunk["CANDIDATO_OU_LEGENDA"] = chunk["NM_VOTAVEL"]
    legenda = tipo.eq("Legenda")
    chunk.loc[legenda, "CANDIDATO_OU_LEGENDA"] = (
        chunk.loc[legenda, "SG_PARTIDO"]
        + " — "
        + chunk.loc[legenda, "NM_PARTIDO"]
    ).str.strip(" —")

    if locais is not None:
        chaves = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO"]
        chunk = chunk.merge(locais, how="left", on=chaves, suffixes=("", "_LOCAL"))
    else:
        for coluna in COLUNAS_LOCALIZACAO:
            chunk[coluna] = ""

    for coluna in COLUNAS_LOCALIZACAO:
        if coluna not in chunk.columns:
            chunk[coluna] = ""

    return chunk[COLUNAS_SAIDA]


def escrever_csv(df: pd.DataFrame, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, sep=";", index=False, encoding="utf-8-sig")


def pivotar_categorias(df: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    resultado = (
        df.groupby(chaves + ["CATEGORIA_VOTO"], dropna=False, observed=True)["QT_VOTOS"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    for categoria in CATEGORIAS_VOTO:
        if categoria not in resultado.columns:
            resultado[categoria] = 0
    resultado["VOTOS_VALIDOS"] = (
        resultado["VALIDO_NOMINAL"] + resultado["VALIDO_LEGENDA"]
    )
    resultado["VOTOS_INVALIDOS_NULOS"] = resultado["NULO"]
    resultado["TOTAL_VOTOS"] = resultado[CATEGORIAS_VOTO].sum(axis=1)
    return resultado


def analisar_csv(
    csv_path: Path,
    saida: Path,
    locais_path: Path | None = None,
    chunksize: int = 100_000,
) -> None:
    saida.mkdir(parents=True, exist_ok=True)
    locais = carregar_localizacoes(locais_path)
    detalhado = saida / "votos_detalhados_df.csv.gz"
    if detalhado.exists():
        detalhado.unlink()

    agregados: list[pd.DataFrame] = []
    linhas = 0
    primeiro_chunk = True
    metricas_secoes: list[pd.DataFrame] = []
    chaves_secao_identidade = [
        "SG_UF",
        "CD_MUNICIPIO",
        "NR_ZONA",
        "NR_SECAO",
        "NR_LOCAL_VOTACAO",
        "NR_URNA_EFETIVADA",
    ]
    chaves_local_identidade = [
        "SG_UF",
        "CD_MUNICIPIO",
        "NR_ZONA",
        "NR_LOCAL_VOTACAO",
    ]

    leitor: Iterable[pd.DataFrame] = pd.read_csv(
        csv_path,
        sep=";",
        encoding="latin1",
        dtype="string",
        keep_default_na=False,
        chunksize=chunksize,
        low_memory=False,
    )

    for numero, bruto in enumerate(leitor, start=1):
        chunk = normalizar_chunk(bruto, locais)
        if chunk.empty:
            continue
        metricas_secao = chunk[chaves_secao_identidade + METRICAS_ELEITORADO].drop_duplicates(
            chaves_secao_identidade
        )
        for coluna in METRICAS_ELEITORADO:
            metricas_secao[coluna] = pd.to_numeric(
                metricas_secao[coluna], errors="coerce"
            ).fillna(0).astype("int64")
        metricas_secoes.append(metricas_secao)
        linhas += len(chunk)
        chunk.to_csv(
            detalhado,
            sep=";",
            index=False,
            mode="wt" if primeiro_chunk else "at",
            header=primeiro_chunk,
            encoding="utf-8-sig" if primeiro_chunk else "utf-8",
            compression="gzip",
        )
        primeiro_chunk = False
        agregados.append(
            chunk.groupby(COLUNAS_AGREGACAO, dropna=False, observed=True)["QT_VOTOS"]
            .sum()
            .reset_index()
        )
        print(f"Processado o bloco {numero}: {linhas:,} linhas do DF", flush=True)

    if not agregados:
        raise RuntimeError("Nenhuma linha do Distrito Federal foi encontrada no CSV.")

    agregado = pd.concat(agregados, ignore_index=True)
    agregado = (
        agregado.groupby(COLUNAS_AGREGACAO, dropna=False, observed=True)["QT_VOTOS"]
        .sum()
        .reset_index()
    )
    metricas_secao = pd.concat(metricas_secoes, ignore_index=True)
    metricas_secao = (
        metricas_secao.groupby(chaves_secao_identidade, as_index=False, observed=True)[
            METRICAS_ELEITORADO
        ]
        .first()
    )

    totais_cargo = pivotar_categorias(agregado, ["DS_CARGO_PERGUNTA", "CD_CARGO_PERGUNTA"])
    escrever_csv(totais_cargo, saida / "totais_por_cargo.csv")

    chaves_secao = [
        "SG_UF",
        "CD_MUNICIPIO",
        "NM_MUNICIPIO",
        "NR_ZONA",
        "NR_SECAO",
        "NR_LOCAL_VOTACAO",
        "NR_URNA_EFETIVADA",
        "NM_LOCAL_VOTACAO",
        "DS_ENDERECO",
        "DS_BAIRRO",
        "NR_CEP",
        "VL_LATITUDE",
        "VL_LONGITUDE",
    ]
    totais_secao = pivotar_categorias(agregado, chaves_secao)
    totais_secao = totais_secao.merge(
        metricas_secao,
        how="left",
        on=chaves_secao_identidade,
    )
    escrever_csv(totais_secao, saida / "totais_por_secao.csv")

    chaves_local = [
        "SG_UF",
        "CD_MUNICIPIO",
        "NM_MUNICIPIO",
        "NR_ZONA",
        "NR_LOCAL_VOTACAO",
        "NM_LOCAL_VOTACAO",
        "DS_ENDERECO",
        "DS_BAIRRO",
        "NR_CEP",
        "VL_LATITUDE",
        "VL_LONGITUDE",
    ]
    metricas_local = (
        metricas_secao.groupby(chaves_local_identidade, as_index=False, observed=True)[
            METRICAS_ELEITORADO
        ]
        .sum()
    )
    totais_local = pivotar_categorias(agregado, chaves_local)
    totais_local = totais_local.merge(
        metricas_local,
        how="left",
        on=chaves_local_identidade,
    )
    escrever_csv(totais_local, saida / "totais_por_local.csv")

    ordenar = [
        "DS_CARGO_PERGUNTA",
        "CATEGORIA_VOTO",
        "NM_PARTIDO",
        "NR_VOTAVEL",
        "NM_VOTAVEL",
    ]
    escrever_csv(
        agregado.sort_values(ordenar, na_position="last"),
        saida / "votos_por_cargo_candidato_legenda.csv",
    )

    presidente = agregado[
        agregado["DS_CARGO_PERGUNTA"].str.contains("Presidente", case=False, na=False)
    ].copy()
    colunas_presidente = [
        *chaves_local_identidade,
        "NM_MUNICIPIO",
        "DS_CARGO_PERGUNTA",
        "CD_CARGO_PERGUNTA",
        "CATEGORIA_VOTO",
        "NR_VOTAVEL",
        "NM_VOTAVEL",
        "CANDIDATO_OU_LEGENDA",
        "NR_PARTIDO",
        "SG_PARTIDO",
        "NM_PARTIDO",
    ]
    presidente = (
        presidente.groupby(colunas_presidente, dropna=False, observed=True)["QT_VOTOS"]
        .sum()
        .reset_index()
    )
    escrever_csv(
        presidente,
        saida / "votos_presidente_por_local.csv",
    )

    locais_preenchidos = 0
    if locais is not None:
        locais_preenchidos = int(agregado["NM_LOCAL_VOTACAO"].astype("string").ne("").sum())

    resumo = [
        "Análise dos Boletins de Urna — Distrito Federal — Eleições 2026",
        f"Fonte CSV: {csv_path}",
        f"Fonte TSE: {URL_DATASET_TSE}",
        f"Pleito: {PLEITO} | Turno: {TURNO} | Eleição estadual/distrital: {CD_ELEICAO_ESTADUAL}",
        f"Linhas de votação processadas: {linhas:,}",
        f"Combinações agregadas: {len(agregado):,}",
        "Categorias: VALIDO_NOMINAL, VALIDO_LEGENDA, BRANCO e NULO.",
        "O TSE identifica o voto como Nulo, mas não publica a causa específica da nulidade no BU/CSV.",
        (
            f"Localizações físicas vinculadas: {locais_preenchidos:,} combinações."
            if locais is not None
            else "Localizações físicas não vinculadas: informe --localizacoes com a tabela do TRE-DF."
        ),
        "Arquivos gerados: votos_detalhados_df.csv.gz, votos_por_cargo_candidato_legenda.csv, "
        "votos_presidente_por_local.csv, totais_por_cargo.csv, totais_por_secao.csv "
        "e totais_por_local.csv.",
    ]
    (saida / "resumo_execucao.txt").write_text("\n".join(resumo) + "\n", encoding="utf-8")
    print(f"Análise concluída. Arquivos gravados em: {saida.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa e analisa os Boletins de Urna oficiais do Distrito Federal."
    )
    parser.add_argument("--baixar", action="store_true", help="Baixa o ZIP oficial do TSE.")
    parser.add_argument(
        "--processar",
        action="store_true",
        help="Processa o CSV extraído e gera os resultados consolidados.",
    )
    parser.add_argument("--url", default=URL_BU_DF, help="URL alternativa do ZIP oficial.")
    parser.add_argument(
        "--zip",
        type=Path,
        default=Path("dados/bweb_1t_DF_051020261403.zip"),
        help="Caminho local do ZIP.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Caminho local do CSV; se omitido, o CSV será extraído do ZIP.",
    )
    parser.add_argument(
        "--localizacoes-tse",
        action="store_true",
        help="Baixa a base oficial do TSE e vincula automaticamente os locais do DF.",
    )
    parser.add_argument(
        "--localizacoes-tse-zip",
        type=Path,
        default=Path("dados/eleitorado_local_votacao_2026.zip"),
        help="Caminho local do ZIP de locais publicado pelo TSE.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path("outputs"),
        help="Pasta de saída dos resultados.",
    )
    parser.add_argument(
        "--localizacoes",
        type=Path,
        default=None,
        help="CSV normalizado do TSE/TRE-DF com zona, endereço e coordenadas.",
    )
    parser.add_argument(
        "--criar-modelo-localizacao",
        type=Path,
        default=None,
        help="Cria um modelo CSV para preencher os endereços do TRE-DF.",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=100_000,
        help="Linhas por bloco na leitura do CSV (padrão: 100000).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.criar_modelo_localizacao is not None:
        criar_modelo_localizacao(args.criar_modelo_localizacao)
        return 0

    if not args.baixar and not args.processar and not args.localizacoes_tse:
        print(__doc__ or "")
        print("Use --baixar --processar para executar o fluxo completo.")
        return 0

    if args.localizacoes_tse:
        if not args.localizacoes_tse_zip.exists():
            baixar_arquivo(URL_LOCALIZACOES_TSE, args.localizacoes_tse_zip)
        csv_localizacoes = extrair_csv_localizacoes_tse(
            args.localizacoes_tse_zip,
            args.localizacoes_tse_zip.parent / args.localizacoes_tse_zip.stem,
        )
        args.localizacoes = args.localizacoes or Path("inputs/local_votacao_df.csv")
        gerar_localizacoes_tse(csv_localizacoes, args.localizacoes)

    if args.baixar:
        baixar_arquivo(args.url, args.zip)

    if args.processar:
        csv_path = args.csv
        if csv_path is None:
            if not args.zip.exists():
                raise FileNotFoundError(
                    f"ZIP não encontrado: {args.zip}. Use --baixar ou informe --zip."
                )
            csv_path = extrair_csv(args.zip, args.zip.parent / args.zip.stem)
        analisar_csv(csv_path, args.saida, args.localizacoes, args.chunksize)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, RuntimeError, requests.RequestException) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise SystemExit(1)
