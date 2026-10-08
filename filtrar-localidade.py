from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


CHAVES_LOCAL = ["CD_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO"]
ARQUIVOS_RESUMO = [
    "totais_por_local.csv",
    "totais_por_secao.csv",
    "votos_presidente_por_local.csv",
]
ARQUIVOS_DETALHADOS = [
    "votos_por_cargo_candidato_legenda.csv",
    "votos_detalhados_df.csv.gz",
]


def normalizar_codigo(valor: str, largura: int) -> str:
    """Normaliza códigos numéricos preservando zeros à esquerda."""
    texto = str(valor).strip()
    return texto.zfill(largura) if texto.isdigit() else texto


def ler_csv(caminho: Path) -> pd.DataFrame:
    """Lê CSVs do pipeline mantendo códigos como texto."""
    return pd.read_csv(
        caminho,
        sep=";",
        dtype="string",
        keep_default_na=False,
        encoding="utf-8-sig",
        compression="infer",
    )


def nome_saida(caminho: Path, destino: Path, identificador: str) -> Path:
    if caminho.name.endswith(".csv.gz"):
        base = caminho.name[:-7]
        extensao = ".csv.gz"
    else:
        base = caminho.stem
        extensao = caminho.suffix
    return destino / f"{base}_{identificador}{extensao}"


def filtrar_arquivo(
    caminho: Path,
    destino: Path,
    filtros: dict[str, str],
    identificador: str,
) -> bool:
    dados = ler_csv(caminho)
    faltantes = [coluna for coluna in CHAVES_LOCAL if coluna not in dados.columns]
    if faltantes:
        print(f"Ignorado {caminho.name}: faltam colunas {', '.join(faltantes)}.")
        return False

    mascara = pd.Series(True, index=dados.index)
    for coluna, valor in filtros.items():
        mascara &= dados[coluna].astype("string").eq(valor)

    filtrado = dados.loc[mascara].copy()
    if filtrado.empty:
        print(f"Nenhum registro encontrado em {caminho.name}.")
        return False

    saida = nome_saida(caminho, destino, identificador)
    compressao = "gzip" if saida.name.endswith(".gz") else None
    filtrado.to_csv(
        saida,
        sep=";",
        index=False,
        encoding="utf-8-sig",
        compression=compressao,
    )
    print(f"{caminho.name}: {len(filtrado):,} registro(s) -> {saida}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Filtra resultados das Eleições 2026 do DF por município, "
            "zona eleitoral e código do local."
        )
    )
    parser.add_argument("--municipio", required=True, help="Código do município, por exemplo 97012.")
    parser.add_argument("--zona", required=True, help="Número da zona eleitoral, por exemplo 1.")
    parser.add_argument("--local", required=True, help="Código do local de votação, por exemplo 1015.")
    parser.add_argument(
        "--entrada",
        type=Path,
        default=Path("outputs"),
        help="Pasta com os resultados completos (padrão: outputs).",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=None,
        help="Pasta de saída; por padrão, entrada/localidades.",
    )
    parser.add_argument(
        "--incluir-detalhado",
        action="store_true",
        help="Também filtra os dois arquivos detalhados, que podem consumir muita memória.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    municipio = normalizar_codigo(args.municipio, 5)
    zona = normalizar_codigo(args.zona, 1)
    local = normalizar_codigo(args.local, 4)
    filtros = {
        "CD_MUNICIPIO": municipio,
        "NR_ZONA": zona,
        "NR_LOCAL_VOTACAO": local,
    }
    identificador = f"municipio{municipio}_zona{zona}_local{local}"
    destino = args.saida or args.entrada / "localidades"
    destino.mkdir(parents=True, exist_ok=True)

    arquivos = list(ARQUIVOS_RESUMO)
    if args.incluir_detalhado:
        arquivos.extend(ARQUIVOS_DETALHADOS)

    encontrados = 0
    for nome in arquivos:
        caminho = args.entrada / nome
        if not caminho.exists():
            print(f"Ausente: {caminho}")
            continue
        encontrados += int(filtrar_arquivo(caminho, destino, filtros, identificador))

    if not encontrados:
        print(
            "Nenhum arquivo foi filtrado. Confira se o processamento foi concluído "
            "e se a chave município/zona/local está correta."
        )
        return 1

    print(f"Arquivos filtrados em: {destino.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
