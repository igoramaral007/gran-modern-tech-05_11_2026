# TechStock Manager

Aplicação web para controle integrado de produtos, licenças, saldos e movimentações da TechStore. Desenvolvida em Python com Flask e banco relacional SQLite.

## Requisitos

- Python 3.10 ou superior
- pip

## Instalação e execução no Windows

Abra o PowerShell na pasta do projeto e execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000` no navegador. Na primeira execução, o sistema cria `techstock.db`, as quatro tabelas relacionais e os dados iniciais de demonstração.

Se a política do PowerShell impedir a ativação do ambiente, execute diretamente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## Banco de dados e carga inicial

O arquivo `database.sql` contém o DDL completo e dados de demonstração: quatro categorias, três fornecedores e seis ativos de hardware, periféricos e software. A aplicação executa esse script automaticamente ao inicializar um banco vazio.

Para criar uma base separada manualmente:

```powershell
sqlite3 techstock.db ".read database.sql"
```

Também é possível escolher outro arquivo de banco definindo a variável `DATABASE_PATH` antes de iniciar a aplicação.

## Funcionalidades

- Painel consolidado com categoria e fornecedor obtidos por `INNER JOIN`, alertas para saldo igual ou inferior ao mínimo e movimentações recentes.
- Cadastro de ativos com categorias e fornecedores selecionados dinamicamente do banco.
- Entradas e saídas com atualização do saldo e inclusão no livro-razão dentro da mesma transação; saídas acima do saldo são impedidas.
- Cadastro de categorias e fornecedores, com proteção referencial e mensagem amigável quando há ativos vinculados.
- Descontinuação lógica de ativos, preservando o histórico de movimentações.

## Regras de integridade

O schema define quatro tabelas (`categories`, `suppliers`, `products`, `movements`), chaves primárias e estrangeiras, nomes de categoria/CNPJ/SKU únicos, preços positivos, saldos não negativos e quantidades movimentadas positivas. Categorias, fornecedores e produtos referenciados não podem ser excluídos fisicamente.

## Testes

Com as dependências instaladas, execute:

```powershell
python -m unittest discover -s tests -v
```
