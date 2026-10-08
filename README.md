# Acompanhamento dos resultados — Eleições 2026

Pipeline em Python para processar os **Boletins de Urna (BU) oficiais do Tribunal Superior Eleitoral (TSE)** e gerar resultados detalhados, agregações e mapa interativo dos locais de votação.

> **Escopo atual:** 1º turno das Eleições 2026 no Distrito Federal (DF).
>
> O TSE publica os Boletins de Urna em pacotes por UF/turno, e não como um download individual por endereço. O projeto baixa o pacote oficial do DF, processa os registros e permite selecionar uma localidade por município, zona eleitoral e código do local depois do processamento.

Para a operação passo a passo, consulte o [Manual rápido de utilização](MANUAL_RAPIDO.md).

## O que o projeto entrega

O pipeline identifica e consolida, por seção, urna e local de votação:

- cargo: Presidente, Governador, Senador, Deputado Federal e Deputado Distrital;
- quantidade de votos;
- voto válido nominal, com número e nome do candidato;
- voto válido de legenda, com número, sigla e nome do partido;
- voto em branco;
- voto nulo;
- município, zona, seção, código do local de votação e número da urna efetivada;
- eleitores aptos, comparecimento e abstenções;
- data/hora de recebimento, abertura, encerramento e emissão do BU;
- nome, endereço, bairro, CEP e coordenadas, quando disponíveis na base oficial de localidades do TSE.

## Limitação importante sobre votos nulos

O arquivo oficial do BU/CSV informa que o voto foi classificado como **Nulo**, inclusive com o código `NR_VOTAVEL=96` no arquivo do DF. Entretanto, o TSE não publica no BU/CSV a causa individual dessa nulidade. Portanto, o projeto não inventa uma justificativa: registra explicitamente:

> `Nulo: classificação oficial do BU; a causa específica da nulidade não é publicada no BU/CSV do TSE.`

Votos em branco aparecem separadamente como `DS_TIPO_VOTAVEL=Branco` e `NR_VOTAVEL=95`.

## Fontes oficiais

- [Conjunto de Boletim de Urna — TSE — Eleições 2026](https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna)
- [ZIP oficial do BU do DF — 1º turno](https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/buweb/bweb_1t_DF_051020261403.zip)
- [Eleitorado por local de votação — TSE — 2026](https://dadosabertos.tse.jus.br/dataset/eleitorado-2026)
- [Instruções técnicas para download dos arquivos de divulgação — TSE](https://www.tse.jus.br/eleicoes/eleicoes-2026-content/arquivos/divulgacao-de-resultados/tse-instrucoes-para-download-dos-arquivos-da-divulgacao-2026)
- [Locais de votação — TRE-DF](https://www.tre-df.jus.br/servicos-eleitorais/locais-de-votacao)
- [OpenFreeMap](https://openfreemap.org/)

O download principal é um pacote do DF. No estado atual do projeto, o programa usa as constantes `UF="DF"`, turno `1` e o conjunto eleitoral de 2026; portanto, não se deve trocar a URL por outro pleito ou UF sem revisar o código e o leiaute.

## Ambiente Miniforge/Mamba

O projeto usa **Miniforge/Mamba**. As instruções abaixo não dependem do Python global do Windows.

No **Miniforge Prompt** ou em um PowerShell com o Miniforge disponível:

```powershell
# Abra o terminal na raiz deste projeto antes de executar os comandos.
mamba env create -f environment.yml
mamba activate eleicoes-2026
```

Se o ambiente já existir:

```powershell
mamba env update -f environment.yml
mamba activate eleicoes-2026
```

O ambiente definido em `environment.yml` contém Python 3.12, pandas, requests e folium. Confira a instalação:

```powershell
mamba env list
python --version
```

## Estrutura do projeto

| Arquivo ou pasta | Finalidade |
|---|---|
| `resultado-eleicoes-2026.py` | Baixa, extrai, normaliza, processa e agrega os Boletins de Urna. |
| `mapa-eleicoes-2026.py` | Gera o mapa HTML interativo dos locais com coordenadas. |
| `filtrar-localidade.py` | Seleciona município, zona e local a partir dos resultados processados. |
| `environment.yml` | Define o ambiente Miniforge/Mamba e as dependências. |
| `README.md` | Visão técnica, fontes e fluxo resumido. |
| `MANUAL_RAPIDO.md` | Manual operacional detalhado. |
| `inputs/local_votacao_df_modelo.csv` | Modelo opcional para localização manual. |
| `dados/` | Downloads e CSVs extraídos; ignorada pelo Git. |
| `outputs/` | Resultados gerados e mapa; ignorada pelo Git. |
| `docs/index.html` | Demonstração pública do mapa, publicada pelo GitHub Pages. |
| `.manus/` e `.work/` | Estado/intermediários locais; ignorados pelo Git. |

Os dados baixados e os resultados gerados não são necessários para instalar o projeto. O repositório deve conter código, documentação, dependências e modelos pequenos; os arquivos brutos podem ser regenerados pelas fontes oficiais.

## Fluxo completo: baixar e processar o DF

O comando abaixo baixa o ZIP de Boletins de Urna, baixa a base oficial de localidades, extrai os CSVs e gera todas as agregações:

```powershell
mamba activate eleicoes-2026

python .\resultado-eleicoes-2026.py `
  --baixar `
  --localizacoes-tse `
  --processar `
  --saida outputs
```

O fluxo:

1. baixa o ZIP oficial do BU do DF;
2. calcula e exibe o SHA-512 do arquivo baixado;
3. extrai o CSV oficial;
4. baixa a base oficial de eleitorado/localidades do TSE;
5. gera `inputs/local_votacao_df.csv` com nome, endereço, bairro, CEP e coordenadas;
6. processa o CSV de votos em blocos para controlar o uso de memória;
7. grava os resultados em `outputs/`.

O download é **em lote para o DF**. A seleção da localidade acontece depois, usando as chaves oficiais.

### Reprocessar usando um ZIP já baixado

Se o ZIP do BU já estiver em `dados/`, não é necessário baixá-lo novamente:

```powershell
mamba activate eleicoes-2026

python .\resultado-eleicoes-2026.py `
  --localizacoes-tse `
  --processar `
  --zip dados\bweb_1t_DF_051020261403.zip `
  --saida outputs
```

Se a tabela de localidades já estiver pronta:

```powershell
python .\resultado-eleicoes-2026.py `
  --processar `
  --zip dados\bweb_1t_DF_051020261403.zip `
  --localizacoes inputs\local_votacao_df.csv `
  --saida outputs
```

## Como obter uma localidade específica

### 1. Entenda a chave da localidade

A chave correta é composta por quatro campos:

```text
SG_UF + CD_MUNICIPIO + NR_ZONA + NR_LOCAL_VOTACAO
```

A zona eleitoral faz parte da chave porque um mesmo código de local pode aparecer em zonas diferentes. Não use apenas o nome do colégio ou apenas o código do local para filtrar.

Exemplo de chave do DF:

```text
UF: DF
Município: 97012
Zona: 1
Local: 1015
```

### 2. Consulte os códigos disponíveis

Depois de executar o fluxo completo, liste os locais conhecidos pela tabela gerada pelo TSE:

```powershell
python -c "import pandas as pd; d=pd.read_csv('inputs/local_votacao_df.csv',sep=';',dtype='string',encoding='utf-8-sig'); print(d[['CD_MUNICIPIO','NR_ZONA','NR_LOCAL_VOTACAO','NM_LOCAL_VOTACAO','DS_BAIRRO']].to_string(index=False))"
```

Use o nome apenas para localizar visualmente o registro; utilize os quatro códigos na seleção final.

### 3. Filtre a localidade

Depois do processamento, use o utilitário incluído no projeto:

```powershell
python .\filtrar-localidade.py `
  --municipio 97012 `
  --zona 1 `
  --local 1015
```

Por padrão, o resultado será salvo em:

```text
outputs/localidades/
```

Serão filtrados os resumos por local, por seção e da Presidência. Para incluir os arquivos mais detalhados, que podem exigir mais memória e espaço, use:

```powershell
python .\filtrar-localidade.py `
  --municipio 97012 `
  --zona 1 `
  --local 1015 `
  --incluir-detalhado
```

A seleção não faz um novo download de um endereço específico: ela reduz os arquivos do pacote oficial já baixado. Isso é necessário porque a fonte pública do TSE é disponibilizada em lote por UF/turno.

### 4. Gerar o mapa da localidade ou do DF

O mapa geral é gerado a partir dos resultados completos:

```powershell
python .\mapa-eleicoes-2026.py `
  --entrada outputs\totais_por_local.csv `
  --presidente outputs\votos_presidente_por_local.csv `
  --saida outputs\mapa_eleicoes_df.html
```

O mapa interativo mostra pontos com votos presidenciais, votos válidos, brancos, nulos, aptos, comparecimento, abstenções e endereço. Ele usa coordenadas publicadas pelo TSE e o estilo público OpenFreeMap; é necessária internet para carregar a camada cartográfica.

## Demonstração visual via GitHub Pages

O mapa final pode ser publicado como uma página estática para que qualquer pessoa veja o resultado sem baixar o projeto. O arquivo publicado deve ficar em `docs/index.html`; a pasta `outputs/` continua ignorada para evitar o envio dos resultados completos e dos arquivos grandes.

### Gerar a demonstração do mapa geral

Depois de concluir o processamento:

```powershell
New-Item -ItemType Directory -Force docs

python .\mapa-eleicoes-2026.py `
  --entrada outputs\totais_por_local.csv `
  --presidente outputs\votos_presidente_por_local.csv `
  --saida docs\index.html
```

Para publicar uma localidade específica, filtre primeiro os resultados e gere o HTML usando os arquivos filtrados:

```powershell
python .\filtrar-localidade.py `
  --municipio 97012 `
  --zona 1 `
  --local 1015

python .\mapa-eleicoes-2026.py `
  --entrada outputs\localidades\totais_por_local_municipio97012_zona1_local1015.csv `
  --presidente outputs\localidades\votos_presidente_por_local_municipio97012_zona1_local1015.csv `
  --saida docs\index.html
```

### Configurar o GitHub Pages

Após o primeiro `push` da branch `main`:

1. abra **Settings** no repositório;
2. entre em **Pages**;
3. em **Build and deployment**, selecione **Deploy from a branch**;
4. selecione a branch `main`;
5. selecione a pasta `/docs`;
6. clique em **Save**.

O endereço esperado será:

```text
https://JosealvjuniorData.github.io/acompanhamento-resultado-eleicoes-2026/
```

Também é possível acessar a demonstração pelo README:

[![Abrir demonstração do mapa](https://img.shields.io/badge/Abrir%20demonstra%C3%A7%C3%A3o%20do%20mapa-GitHub%20Pages-2ea44f?logo=github)](https://JosealvjuniorData.github.io/acompanhamento-resultado-eleicoes-2026/)

Se `main` não aparecer na configuração do Pages, faça primeiro o commit e o `push` dessa branch. O repositório precisa ter pelo menos um commit remoto antes que a branch possa ser escolhida.

O HTML usa MapLibre e OpenFreeMap, portanto a demonstração precisa de internet para carregar o fundo cartográfico. O GitHub Pages publica o conteúdo na internet; revise o mapa e os dados incorporados antes do `push`.

Quando os dados forem atualizados, gere novamente `docs/index.html`, revise a demonstração e publique a alteração:

```powershell
git add README.md docs\index.html
git commit -m "Atualiza demonstração do mapa"
git push
```

## Arquivos gerados

| Arquivo | Conteúdo |
|---|---|
| `votos_detalhados_df.csv.gz` | Registro detalhado por seção, urna, cargo, candidato/legenda e categoria de voto. |
| `votos_por_cargo_candidato_legenda.csv` | Votos agregados por cargo, candidato/legenda e seção/local. |
| `votos_presidente_por_local.csv` | Votos presidenciais por zona, local, candidato, válidos, brancos e nulos. |
| `totais_por_cargo.csv` | Totais de válidos nominais, legenda, brancos, nulos e total por cargo. |
| `totais_por_secao.csv` | Totais por seção/urna, com aptos, comparecimento, abstenções e localização. |
| `totais_por_local.csv` | Totais consolidados por zona/local, com métricas de eleitorado e coordenadas. |
| `resumo_execucao.txt` | Fonte, parâmetros, contagens e limitações da execução. |

## Modo manual de localização

Se a base oficial do TSE não puder ser usada, crie um modelo:

```powershell
python .\resultado-eleicoes-2026.py `
  --criar-modelo-localizacao inputs\local_votacao_df_modelo.csv
```

Preencha o CSV separado por ponto e vírgula e mantenha obrigatoriamente:

- `SG_UF`;
- `CD_MUNICIPIO`;
- `NR_ZONA`;
- `NR_LOCAL_VOTACAO`.

Os campos de nome, endereço, bairro, CEP, latitude, longitude e fonte são complementares. A preferência é sempre a base oficial gerada com `--localizacoes-tse`.

## Armazenamento e publicação no Git

O `.gitignore` impede o envio de dados brutos, saídas grandes, estado local do Manus, ZIPs, caches, ambientes e segredos. Isso é intencional: o GitHub deve armazenar o código e a documentação, enquanto os dados podem ser baixados novamente das fontes oficiais.

`docs/index.html` é a exceção intencional: ele contém somente a demonstração escolhida para o GitHub Pages. Não copie a pasta `outputs/` inteira para `docs/`.

Não publique arquivos `.env`, tokens, credenciais ou arquivos individuais maiores que 100 MB. Antes do primeiro commit, revise:

```powershell
git add .
git status --short
git diff --cached --stat
git diff --cached --name-only
git check-ignore -v dados\bweb_1t_DF_051020261403.zip
```

## Atualização e reprodutibilidade

Quando o TSE publicar um novo arquivo compatível:

1. confira UF, turno, pleito e data do arquivo;
2. execute o download ou informe o novo `--zip`;
3. regenere a tabela de localidades;
4. reprocesse os resultados;
5. gere novamente o mapa;
6. confira `outputs/resumo_execucao.txt`.

Não substitua o ZIP por outro pleito sem revisar as constantes e o leiaute do programa. O projeto registra o SHA-512 do download para facilitar a conferência da fonte utilizada.

## Licença e uso dos dados

Os dados são provenientes de fontes públicas oficiais. Verifique as condições de uso e a atribuição exigida por cada fonte antes de redistribuir arquivos brutos. O código deste projeto e os dados oficiais não devem ser tratados automaticamente como se tivessem a mesma licença.
