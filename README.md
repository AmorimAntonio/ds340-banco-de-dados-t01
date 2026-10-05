# Pipeline ETL e Data Warehouse Multidimensional — Loja de Varejo

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Pandas-2.0%2B-150458.svg)](https://pandas.pydata.org/)
[![SQL Server](https://img.shields.io/badge/Source-SQL%20Server-CC292B.svg)](https://www.microsoft.com/sql-server)
[![MySQL](https://img.shields.io/badge/Target-MySQL-4479A1.svg)](https://www.mysql.com/)

Repositório da solução automatizada de **ETL (Extract, Transform, Load)** desenvolvida para a disciplina **DS340 — Banco de Dados 3** do curso de Tecnologia em Análise e Desenvolvimento de Sistemas da **Universidade Federal do Paraná (UFPR)**.

---

## Sobre o Projeto

O objetivo do projeto é construir um **Data Warehouse (DW) Multidimensional** pré-agregado para uma rede de lojas de varejo. 

A pipeline extrai os dados transacionais (OLTP) de uma base de origem em **SQL Server**, processa e gera um **Cubo ROLAP multidimensional completo em memória RAM** utilizando Python/Pandas, e persiste a tabela fato pré-sumarizada em um banco multidimensional no **MySQL**.

### Diferencial da Abordagem (Pandas ETL em Memória)
* **Desempenho de Leitura (Zero `GROUP BY` na Análise):** Todas as $2^8 = 256$ combinações possíveis de agrupamento entre as 8 dimensões são pré-calculadas na fase de ETL. As consultas analíticas no DW utilizam apenas restrições `WHERE ... IS NULL` e `WHERE ... IS NOT NULL`.
* **Tratamento de Anomalias de Origem:** Eliminação do risco de explosão por produto cartesiano na extração atômica via subqueries agregadas (`UNION ALL` com `DISTINCT`).
* **Processamento Desacoplado:** A carga computacional pesada de agregação é transferida do motor do banco de dados para a memória da aplicação em Python.

---

## Arquitetura da Solução

```mermaid
graph LR
    subgraph Origem [OLTP - SQL Server]
        A[(Base ADS)]
    end

    subgraph ETL [Pipeline Python / Pandas]
        B[1. Extração Atômica com pyodbc]
        C[2. Mapeamento De-Para / Surrogate Keys]
        D[3. Cubo ROLAP com itertools + Pandas]
    end

    subgraph Destino [OLAP - MySQL]
        E[(Dimensões)]
        F[(Fato Venda Pré-sumarizada)]
    end

    A --> B
    B --> C
    C --> E
    C --> D
    D --> F