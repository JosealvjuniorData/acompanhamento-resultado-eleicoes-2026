# Manual operacional — Acompanhamento dos resultados das Eleições 2026

## 1. Objetivo e escopo

Este projeto processa os **Boletins de Urna (BU) oficiais do TSE** e produz resultados por cargo, seção, urna e local de votação, além de um mapa interativo.

O estado atual está configurado para:

- **UF:** Distrito Federal (`DF`);
- **turno:** 1º turno;
- **eleição:** Eleições 2026;
- **fonte principal:** conjunto oficial de Boletins de Urna do TSE;
- **localização física:** base oficial de eleitorado/local de votação do TSE.

> O download oficial é feito em lote para a UF/turno. Não existe, neste fluxo, um endpoint que baixe somente um colégio ou endereço. Para obter uma localidade específica, primeiro baixe e processe o pacote do DF; depois filtre por município, zona e código do local.

> O BU classifica o voto como `Nulo`, mas não publica a causa individual da nulidade. O projeto preserva essa limitação e não cria uma justificativa que não esteja na fonte oficial.

---

## 2. Requisitos

- Windows ou outro sistema com Python compatível;
- Python 3.12 recomendado;
- um gerenciador de ambiente: Miniforge/Mamba, Conda ou `venv` + `pip`;
- internet para baixar as fontes oficiais;
- internet para carregar o mapa OpenFreeMap;
- espaço livre recomendado de pelo menos **2 GB**, considerando ZIP, CSV extraído, resultados intermediários e folga;
- memória suficiente para processar CSVs grandes. O pipeline lê o BU em blocos, mas alguns filtros detalhados podem consumir mais memória.

O ambiente está definido em `environment.yml`:

```yaml
name: eleicoes-2026
channels:
  - conda-forge
dependencies:
  - python=3.12
  - pandas>=2.2
  - requests>=2.32
  - folium>=0.17
```

O arquivo `requirements.txt` contém as mesmas dependências para quem preferir instalar com `pip` em um ambiente `venv` ou em uma instalação Python convencional.

---

## 3. Preparar o ambiente Python

O projeto não exige Miniforge. Para o desenvolvimento deste projeto, a opção recomendada é Miniforge/Mamba, mas as opções abaixo são equivalentes para quem estiver usando outro computador.

Entre na pasta do projeto:

```powershell
# Abra o terminal na raiz deste projeto antes de executar os comandos.
```

### 3.1 Miniforge/Mamba — opção recomendada para este projeto

Na primeira utilização, crie o ambiente:

```powershell
mamba env create -f environment.yml
mamba activate eleicoes-2026
```

Se o ambiente já existir, atualize-o:

```powershell
mamba env update -f environment.yml
mamba activate eleicoes-2026
```

### 3.2 Conda — alternativa compatível

O `environment.yml` segue o formato padrão de ambientes Conda:

```powershell
conda env create -f environment.yml
conda activate eleicoes-2026
```

### 3.3 Python `venv` + `pip` — alternativa universal

Com Python 3.12 instalado:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

No Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3.4 Conferir a instalação

```powershell
python --version
```

Com Miniforge/Mamba ou Conda, o ambiente ativo deverá ser `eleicoes-2026`. Com `venv`, o prompt normalmente exibirá o nome `.venv`.

---

## 4. Arquivos principais

| Arquivo ou pasta | Finalidade |
|---|---|
| `resultado-eleicoes-2026.py` | Programa principal: baixa, extrai, normaliza e agrega o BU. |
| `mapa-eleicoes-2026.py` | Gera o HTML do mapa interativo. |
| `filtrar-localidade.py` | Filtra os resultados para um município, zona e local escolhidos. |
| `environment.yml` | Define um ambiente Conda-compatível e suas dependências. |
| `requirements.txt` | Dependências para instalação com `pip` em `venv` ou Python convencional. |
| `README.md` | Visão técnica, fontes e fluxo resumido. |
| `MANUAL_RAPIDO.md` | Este manual operacional. |
| `dados/` | ZIPs e CSVs extraídos do TSE; dados locais, ignorados pelo Git. |
| `inputs/local_votacao_df.csv` | Localizações geradas automaticamente pela base oficial; arquivo derivado. |
| `inputs/local_votacao_df_modelo.csv` | Modelo para preenchimento manual, usado apenas como alternativa. |
| `outputs/` | Resultados processados e mapa; arquivos gerados, ignorados pelo Git. |
| `.manus/` e `.work/` | Estado e intermediários locais; não são necessários para o usuário final. |

---

## 5. Download e processamento completo do DF

Este é o fluxo recomendado para uma instalação nova:

```powershell
python .\resultado-eleicoes-2026.py `
  --baixar `
  --localizacoes-tse `
  --processar `
  --saida outputs
```

O comando executa as etapas abaixo:

1. baixa o ZIP oficial de Boletins de Urna do DF;
2. grava o download em `dados/` e exibe o SHA-512;
3. extrai o CSV oficial em uma subpasta de `dados/`;
4. baixa a base de eleitorado/localidades do TSE;
5. seleciona o arquivo do DF dessa base;
6. gera `inputs/local_votacao_df.csv`;
7. processa o BU em blocos de 100.000 linhas;
8. gera os arquivos consolidados em `outputs/`.

O download pode demorar e exige espaço temporário. Não interrompa o processo durante a gravação de um arquivo grande, salvo se necessário.

### Ver as opções disponíveis

```powershell
python .\resultado-eleicoes-2026.py --help
```

### Ajustar o tamanho dos blocos

O padrão é 100.000 linhas. Se a máquina tiver pouca memória, use um bloco menor:

```powershell
python .\resultado-eleicoes-2026.py `
  --localizacoes-tse `
  --processar `
  --zip dados\bweb_1t_DF_051020261403.zip `
  --saida outputs `
  --chunksize 50000
```

---

## 6. Reprocessar sem baixar novamente

Se o ZIP já existir em `dados/`:

```powershell
python .\resultado-eleicoes-2026.py `
  --localizacoes-tse `
  --processar `
  --zip dados\bweb_1t_DF_051020261403.zip `
  --saida outputs
```

Se a tabela de localidades já estiver pronta e não precisar ser atualizada:

```powershell
python .\resultado-eleicoes-2026.py `
  --processar `
  --zip dados\bweb_1t_DF_051020261403.zip `
  --localizacoes inputs\local_votacao_df.csv `
  --saida outputs
```

O processamento atual substitui os resultados consolidados na pasta informada em `--saida`. Isso evita misturar arquivos de execuções antigas e novas.

---

## 7. Como localizar o código do endereço desejado

A identificação correta usa quatro campos:

```text
SG_UF + CD_MUNICIPIO + NR_ZONA + NR_LOCAL_VOTACAO
```

A zona eleitoral é obrigatória porque o mesmo código de local pode aparecer em zonas diferentes.

Depois de executar o download com `--localizacoes-tse`, consulte os locais:

```powershell
python -c "import pandas as pd; d=pd.read_csv('inputs/local_votacao_df.csv',sep=';',dtype='string',encoding='utf-8-sig'); print(d[['CD_MUNICIPIO','NR_ZONA','NR_LOCAL_VOTACAO','NM_LOCAL_VOTACAO','DS_BAIRRO']].to_string(index=False))"
```

Para procurar por parte do nome ou bairro:

```powershell
python -c "import pandas as pd; d=pd.read_csv('inputs/local_votacao_df.csv',sep=';',dtype='string',encoding='utf-8-sig'); m=d['NM_LOCAL_VOTACAO'].str.contains('ESCOLA',case=False,na=False) | d['DS_BAIRRO'].str.contains('ASA SUL',case=False,na=False); print(d.loc[m,['CD_MUNICIPIO','NR_ZONA','NR_LOCAL_VOTACAO','NM_LOCAL_VOTACAO','DS_BAIRRO']].to_string(index=False))"
```

Use o texto apenas para descobrir o registro. Na etapa seguinte, informe os códigos.

---

## 8. Filtrar uma localidade específica

O utilitário `filtrar-localidade.py` reduz os resultados completos para um município, zona e local:

```powershell
python .\filtrar-localidade.py `
  --municipio 97012 `
  --zona 1 `
  --local 1015
```

Os arquivos serão gravados em `outputs/localidades/`.

Por padrão, são filtrados:

- `totais_por_local.csv`;
- `totais_por_secao.csv`;
- `votos_presidente_por_local.csv`.

Exemplo de saída:

```text
outputs/localidades/
├── totais_por_local_municipio97012_zona1_local1015.csv
├── totais_por_secao_municipio97012_zona1_local1015.csv
└── votos_presidente_por_local_municipio97012_zona1_local1015.csv
```

Para incluir os arquivos detalhados, que podem ser grandes:

```powershell
python .\filtrar-localidade.py `
  --municipio 97012 `
  --zona 1 `
  --local 1015 `
  --incluir-detalhado
```

O modo detalhado também filtra `votos_detalhados_df.csv.gz` e `votos_por_cargo_candidato_legenda.csv`. Use-o somente quando precisar dos registros por candidato/legenda e tiver espaço e memória disponíveis.

### Por que o projeto baixa o DF inteiro?

O arquivo disponibilizado pelo TSE é um pacote oficial consolidado por UF/turno. O projeto não faz requisições individuais por colégio porque essa não é a forma como o conjunto oficial de 2026 é publicado. O filtro local preserva a fonte oficial e cria uma cópia menor para análise do endereço desejado.

---

## 9. Arquivos gerados

### `votos_detalhados_df.csv.gz`

Registros processados por município, zona, seção, urna, cargo, candidato/legenda, categoria do voto e quantidade de votos. É o arquivo mais detalhado e pode ser grande.

### `votos_por_cargo_candidato_legenda.csv`

Agregação por cargo, candidato/legenda e seção/local. É útil para comparar candidatos, partidos e cargos em uma localidade.

### `votos_presidente_por_local.csv`

Votos da Presidência agrupados por município, zona, local e categoria. É usado pelo mapa e pelo filtro de localidade.

### `totais_por_cargo.csv`

Totais gerais por cargo, sem chave de localidade. Por isso, não é filtrado pelo utilitário de local.

### `totais_por_secao.csv`

Totais por seção e urna, com aptos, comparecimento, abstenções e localização quando disponível.

### `totais_por_local.csv`

Consolidação por local de votação, com endereço, coordenadas, votos e métricas de eleitorado.

### `resumo_execucao.txt`

Registra a fonte, os parâmetros, as linhas processadas, as combinações agregadas, as localizações vinculadas e as limitações da execução.

---

## 10. Gerar o mapa

Depois do processamento completo:

```powershell
python .\mapa-eleicoes-2026.py `
  --entrada outputs\totais_por_local.csv `
  --presidente outputs\votos_presidente_por_local.csv `
  --saida outputs\mapa_eleicoes_df.html
```

Abra no Windows:

```powershell
Start-Process (Resolve-Path outputs\mapa_eleicoes_df.html)
```

Se o navegador não carregar a camada cartográfica ao abrir com `file://`, use um servidor local:

```powershell
python -m http.server 8000 --directory outputs
```

Abra:

```text
http://localhost:8000/mapa_eleicoes_df.html
```

Para encerrar o servidor, pressione `Ctrl+C` no terminal.

O mapa usa MapLibre e o estilo público do OpenFreeMap. Não é necessária chave de API, mas é necessária internet para a camada de fundo.

Ao clicar em um ponto, o popup exibe:

- local, município, zona e código;
- eleitores aptos;
- comparecimento e percentual;
- abstenções e percentual;
- candidatos à Presidência e votos;
- votos válidos, brancos e nulos;
- endereço, bairro e CEP quando disponíveis.

---

## 11. Localização manual alternativa

A base oficial do TSE é a opção recomendada. Se for necessário preencher uma tabela complementar manualmente:

```powershell
python .\resultado-eleicoes-2026.py `
  --criar-modelo-localizacao inputs\local_votacao_df_modelo.csv
```

O arquivo deve manter, obrigatoriamente:

- `SG_UF`;
- `CD_MUNICIPIO`;
- `NR_ZONA`;
- `NR_LOCAL_VOTACAO`.

Os demais campos são:

- `NM_LOCAL_VOTACAO`;
- `DS_ENDERECO`;
- `DS_BAIRRO`;
- `NR_CEP`;
- `VL_LATITUDE`;
- `VL_LONGITUDE`;
- `FONTE_LOCALIZACAO`.

Depois de preencher o arquivo:

```powershell
python .\resultado-eleicoes-2026.py `
  --processar `
  --zip dados\bweb_1t_DF_051020261403.zip `
  --localizacoes inputs\local_votacao_df_modelo.csv `
  --saida outputs
```

A fonte da tabela manual deve ser registrada no campo `FONTE_LOCALIZACAO`.

---

## 12. Atualizar os dados

Quando houver novo arquivo oficial:

1. confirme a UF, o turno, o pleito e a data;
2. baixe o ZIP correspondente ou use `--url`/`--zip` conforme o leiaute suportado;
3. gere novamente a tabela de localidades;
4. reprocesse o BU;
5. filtre novamente a localidade desejada;
6. gere novamente o mapa;
7. revise `outputs/resumo_execucao.txt`.

O programa atual foi escrito para o leiaute e as constantes do DF no 1º turno de 2026. Não substitua o ZIP por outro pleito sem revisar o código.

---

## 13. Publicação no GitHub

O projeto possui um `.gitignore` para evitar o envio de:

- ZIPs e dados brutos;
- CSVs extraídos;
- resultados gerados;
- estado do Manus e intermediários;
- ambientes e caches;
- segredos e arquivos `.env`.

Antes do primeiro commit:

```powershell
git add .
git status --short
git diff --cached --stat
git diff --cached --name-only
git check-ignore -v dados\bweb_1t_DF_051020261403.zip
```

O repositório deve conter o código, `environment.yml`, documentação e o modelo de localização. Os dados oficiais podem ser baixados novamente por quem clonar o projeto.

---

## 14. Solução de problemas

### O comando do ambiente não é reconhecido

Escolha uma das opções da seção 3: abra o Miniforge Prompt para usar Mamba, inicialize o Conda ou crie um `.venv` e instale `requirements.txt` com `pip`. O importante é executar os scripts com o ambiente escolhido ativado.

### O ZIP não foi encontrado

Use `--baixar` ou informe o caminho correto:

```powershell
python .\resultado-eleicoes-2026.py `
  --processar `
  --zip dados\bweb_1t_DF_051020261403.zip `
  --localizacoes inputs\local_votacao_df.csv `
  --saida outputs
```

### Não foi encontrada a localidade

Confira se município, zona e local foram informados com a chave correta. Liste `inputs/local_votacao_df.csv` e não filtre somente pelo nome do colégio.

### O filtro não encontra registros

Verifique se o processamento foi concluído e se os arquivos estão em `outputs/`. Execute primeiro o fluxo completo e confira `outputs/resumo_execucao.txt`.

### O filtro detalhado usa muita memória

Comece sem `--incluir-detalhado`. Os resumos por local, seção e Presidência são normalmente suficientes. Use o modo detalhado apenas quando precisar dos registros completos.

### O mapa apresenta erro de colunas

Os arquivos podem ter sido gerados por uma versão anterior. Reprocesse o BU com a versão atual do pipeline e gere o mapa novamente.

### O mapa não carrega o fundo

Confira a internet e abra pelo servidor local:

```powershell
python -m http.server 8000 --directory outputs
```

Depois acesse `http://localhost:8000/mapa_eleicoes_df.html`.

### Por que um voto nulo foi anulado?

O BU publicado pelo TSE informa a classificação `Nulo`, mas não publica a causa individual. O projeto registra essa limitação e não atribui uma causa que não esteja na fonte oficial.

---

## 15. Fontes e atribuições

- [Boletins de Urna — TSE — Eleições 2026](https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna)
- [ZIP oficial do BU do DF — 1º turno](https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/buweb/bweb_1t_DF_051020261403.zip)
- [Eleitorado por local de votação — TSE — 2026](https://dadosabertos.tse.jus.br/dataset/eleitorado-2026)
- [Locais de votação — TRE-DF](https://www.tre-df.jus.br/servicos-eleitorais/locais-de-votacao)
- [OpenFreeMap](https://openfreemap.org/)
- [OpenMapTiles](https://www.openmaptiles.org/)
- [OpenStreetMap — copyright](https://www.openstreetmap.org/copyright)

Confira as condições de uso de cada fonte antes de redistribuir arquivos brutos. Código e dados oficiais podem ter condições de uso diferentes.
