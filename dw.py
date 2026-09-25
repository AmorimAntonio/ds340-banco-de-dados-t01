"""
Requisitos:
    pip install pyodbc pymysql pandas
"""

import pyodbc
import pymysql
import pandas as pd
from itertools import combinations

# ----------------------------------------------------------------------
# 1. conexões
# editem as credenciais aqui pra ficar compatível com o que vcs configuraram
# ----------------------------------------------------------------------

def conectar_origem():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;" 
        "DATABASE=ADS;"
        "Trusted_Connection=yes;"
    )

def conectar_destino():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="6767",
        database="dw_vendas",
        autocommit=False, # pra só salvar os dados se n tiver erro
    )

# ----------------------------------------------------------------------
# 2. carga das dimensões:
#  2.1 primeiro select pra pegar os dados na origem
#  2.2 insere os dados na tabela do mysql
#  2.3 volta um dicionario que associa o id original (tipo um cpf de cliente
#       ou matricula) com um novo id gerado no dw (no mysql)
# ----------------------------------------------------------------------

def carregar_dim_tipo(conn_dest):
    """insere manualmente pq nao tem na fonte"""
    cur = conn_dest.cursor()
    mapa = {}
    for nome in ["Alimento", "Eletro", "Vestuario"]:
        cur.execute("INSERT INTO tipo (nome_tipo) VALUES (%s)", (nome,))
        mapa[nome] = cur.lastrowid
    conn_dest.commit()
    return mapa

def carregar_dim_categoria(conn_origem, conn_dest):
    cur_o = conn_origem.cursor()
    cur_o.execute("SELECT tb013_cod_categoria, tb013_descricao FROM tb013_categorias")
    linhas = cur_o.fetchall()

    cur_d = conn_dest.cursor()
    mapa = {}
    for cod, descricao in linhas:
        cur_d.execute("INSERT INTO categoria (nome_categoria) VALUES (%s)", (descricao,))
        mapa[cod] = cur_d.lastrowid
    conn_dest.commit()
    return mapa

def carregar_dim_funcionario(conn_origem, conn_dest):
    cur_o = conn_origem.cursor()
    cur_o.execute("""
        SELECT f.tb005_matricula, f.tb005_nome_completo, c.tb006_nome_cargo
        FROM tb005_funcionarios f
        LEFT JOIN tb005_006_funcionarios_cargos fc ON f.tb005_matricula = fc.tb005_matricula
        LEFT JOIN tb006_cargos c ON fc.tb006_cod_cargo = c.tb006_cod_cargo
    """)
    linhas = cur_o.fetchall()

    cur_d = conn_dest.cursor()
    mapa = {}
    for matricula, nome, cargo in linhas:
        cur_d.execute(
            "INSERT INTO funcionario (nome_completo, cargo) VALUES (%s, %s)",
            (nome, cargo),
        )
        mapa[matricula] = cur_d.lastrowid
    conn_dest.commit()
    return mapa

def carregar_dim_cliente(conn_origem, conn_dest):
    cur_o = conn_origem.cursor()
    cur_o.execute("SELECT tb010_cpf, tb010_nome FROM tb010_clientes")
    linhas = cur_o.fetchall()

    cur_d = conn_dest.cursor()
    mapa = {}
    for cpf, nome in linhas:
        cur_d.execute("INSERT INTO cliente (nome) VALUES (%s)", (nome,))
        mapa[cpf] = cur_d.lastrowid
    conn_dest.commit()
    return mapa

def carregar_dim_loja(conn_origem, conn_dest):
    cur_o = conn_origem.cursor()
    cur_o.execute("""
        SELECT l.tb004_cod_loja, c.tb002_nome_cidade, e.tb001_sigla_uf
        FROM tb004_lojas l
        JOIN tb003_enderecos e ON l.tb003_cod_endereco = e.tb003_cod_endereco
        JOIN tb002_cidades c ON e.tb002_cod_cidade = c.tb002_cod_cidade
    """)
    linhas = cur_o.fetchall()

    cur_d = conn_dest.cursor()
    mapa = {}
    for cod_loja, cidade, uf in linhas:
        cur_d.execute("INSERT INTO loja (cidade, uf) VALUES (%s, %s)", (cidade, uf))
        mapa[cod_loja] = cur_d.lastrowid
    conn_dest.commit()
    return mapa

def carregar_dim_canal(conn_dest):
    cur = conn_dest.cursor()
    mapa = {}
    for nome in ["Loja Física", "Loja Virtual"]:
        cur.execute("INSERT INTO canal (nome_canal) VALUES (%s)", (nome,))
        mapa[nome] = cur.lastrowid
    conn_dest.commit()
    return mapa

def carregar_dim_mes(conn_dest):
    nomes = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    cur = conn_dest.cursor()
    mapa = {}
    for numero, nome in enumerate(nomes, start=1):
        cur.execute("INSERT INTO mes (nome_mes) VALUES (%s)", (nome,))
        mapa[numero] = cur.lastrowid
    conn_dest.commit()
    return mapa

def carregar_dim_ano(conn_origem, conn_dest):
    cur_o = conn_origem.cursor()
    cur_o.execute("SELECT DISTINCT YEAR(tb010_012_data) FROM tb010_012_vendas") 
    anos = [linha[0] for linha in cur_o.fetchall()]

    cur_d = conn_dest.cursor()
    mapa = {}
    for ano in anos:
        cur_d.execute("INSERT INTO ano (pk_ano) VALUES (%s)", (ano,))
        mapa[ano] = ano 
    conn_dest.commit()
    return mapa

# ----------------------------------------------------------------------
# 3. carregando os dados na tabela fato via pandas
#   3.1 faz uma query com a maior granularidade possível p pegar as infos
#   3.2 cria um dataframe e traduz as chaves da origem pras pks do dw
#   3.3 cria o cubo rolap completo pré-agregado com todas as combinações
#   3.4 insere tudo no bd com NULL nas dimensões não agrupadas
# ----------------------------------------------------------------------

def processar_fato_pandas(conn_origem, conn_dest, mapas):
    # 3.1 - query p buscar os dados no nivel mais detalhado possível
    # ela pega o cpf do cliente, a matricula do funcionario, a categoria, a loja,
    # o mês, o ano, a quantidade, o valor, o tipo de produto, o tipo de loja
    # para ter as informações de cada venda com a maior granularidade possível
    query_detalhada = """
        SELECT 
            v.tb010_cpf AS cpf_cliente,
            v.tb005_matricula AS matricula_func,
            p.tb013_cod_categoria AS cod_categoria,
            f.tb004_cod_loja AS cod_loja,
            MONTH(v.tb010_012_data) AS mes,
            YEAR(v.tb010_012_data) AS ano,
            v.tb010_012_quantidade AS qtd,
            (v.tb010_012_quantidade * v.tb010_012_valor_unitario) AS valor,
            sub.tipo AS tipo_produto,
            CASE 
                WHEN l.tb010_cpf IS NOT NULL THEN 'Loja Virtual' 
                ELSE 'Loja Física' 
            END AS canal
        FROM tb010_012_vendas v
        JOIN tb012_produtos p ON v.tb012_cod_produto = p.tb012_cod_produto
        JOIN (
            SELECT tb005_matricula, MIN(tb004_cod_loja) AS tb004_cod_loja 
            FROM tb005_funcionarios 
            GROUP BY tb005_matricula
        ) f ON v.tb005_matricula = f.tb005_matricula
        LEFT JOIN (
            SELECT DISTINCT tb012_cod_produto AS cod, 'Alimento' AS tipo FROM tb014_prd_alimentos
            UNION ALL
            SELECT DISTINCT tb012_cod_produto, 'Eletro' FROM tb015_prd_eletros
            UNION ALL
            SELECT DISTINCT tb012_cod_produto, 'Vestuario' FROM tb016_prd_vestuarios
        ) sub ON p.tb012_cod_produto = sub.cod
        LEFT JOIN (SELECT DISTINCT tb010_cpf FROM tb011_logins) l ON v.tb010_cpf = l.tb010_cpf
    """
    
    cur_o = conn_origem.cursor()
    cur_o.execute(query_detalhada)
    colunas = [desc[0] for desc in cur_o.description]
    dados = cur_o.fetchall()
    
        
    # pega o resultado disso e carrega em uma tupla pro pandas fazer as agregações dps
    df = pd.DataFrame([tuple(row) for row in dados], columns=colunas)
    
    # 3.2 - substituindo os IDs de origem pelos ids para as chaves no mysql
    # (ele pega as chaves criadas na etapa 2 com um map)
    df['fk_cliente'] = df['cpf_cliente'].map(mapas['cliente'])
    df['fk_funcionario'] = df['matricula_func'].map(mapas['funcionario'])
    df['fk_categoria'] = df['cod_categoria'].map(mapas['categoria'])
    df['fk_loja'] = df['cod_loja'].map(mapas['loja'])
    df['fk_mes'] = df['mes'].map(mapas['mes'])
    df['fk_ano'] = df['ano'].map(mapas['ano'])
    df['fk_tipo'] = df['tipo_produto'].map(mapas['tipo'])
    df['fk_canal'] = df['canal'].map(mapas['canal'])
    
    # pra mapear todas as fks que tem na fato
    todas_fks = ['fk_tipo', 'fk_categoria', 'fk_funcionario', 'fk_cliente', 
                 'fk_loja', 'fk_canal', 'fk_mes', 'fk_ano']
                 
    # mantem só as chaves convertidas e as metricas
    df_base = df[todas_fks + ['qtd', 'valor']].copy()
    
    # 3.3 - cria o cubo rolap completo pré-agregado (256 combinações, intertools)
    # gera todas as combinações de agrupamento possíveis para responder a qualquer pergunta sem group by
    lista_dfs = []

    # total geral (todas as FKs como None)
    total = df_base[['qtd', 'valor']].sum().to_frame().T
    for fk in todas_fks:
        total[fk] = None
    lista_dfs.append(total)

    # gera as combinações de 1 até 8 dimensões (255 combinações)
    for r in range(1, len(todas_fks) + 1):
        for comb in combinations(todas_fks, r):
            fks_agrupadas = list(comb)
            
            # faz o groupby no nível dessa combinação
            df_agrupado = df_base.groupby(fks_agrupadas, as_index=False)[['qtd', 'valor']].sum()
            
            # as colunas que não fizeram parte desse agrupamento recebem None
            for fk in todas_fks:
                if fk not in fks_agrupadas:
                    df_agrupado[fk] = None
                    
            lista_dfs.append(df_agrupado)

    # une todos os cenarios de agrupamentos do cubo
    df_fato_final = pd.concat(lista_dfs, ignore_index=True)
    
    # converte NaN do pandas para None, pro pymysql conseguir inserir NULL no bd
    df_fato_final = df_fato_final.astype(object).where(pd.notna(df_fato_final), None)
    
    # 3.4 - insere no banco destino
    cur_d = conn_dest.cursor()
    
    # garante a ordem das colunas pra bater com o insert
    df_fato_final = df_fato_final[todas_fks + ['qtd', 'valor']]
    
    # itera linha a linha do dataframe e manda pro mysql
    linhas_inseridas = 0
    for row in df_fato_final.itertuples(index=False, name=None):
        cur_d.execute("""
            INSERT INTO fato_venda
                (fk_tipo, fk_categoria, fk_funcionario, fk_cliente,
                fk_loja, fk_canal, fk_mes, fk_ano, quantidade, valor)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, row)
        linhas_inseridas += 1
        
    conn_dest.commit()
    print(f"Carga na tabela fato concluída com pandas, {linhas_inseridas} linhas inseridas com sumarização total.")

# ----------------------------------------------------------------------
# 4. orquestração
#   4.1 conecta com o banco
#   4.2 limpa as tabelas do dw pra evitar duplicidade qnd rodar dnv 
#   4.3 faz a carga nas dimensoes
#   4.4 faz a carga na fato usando pandas com o dicionario de mapas
#   4.5 finaliza e fecha as conexoes com o banco
# ----------------------------------------------------------------------

def limpar_banco_destino(conn_dest):
    """limpa as tabelas do dw pra nao duplicar dados ao reexecutar"""
    cur = conn_dest.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    tabelas = [
        "fato_venda", "tipo", "categoria", "funcionario",
        "cliente", "loja", "canal", "mes", "ano"
    ]
    for tab in tabelas:
        cur.execute(f"TRUNCATE TABLE {tab}")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn_dest.commit()
    print("Banco de destino limpo com sucesso.")


def main():
    conn_origem = conectar_origem()
    conn_destino = conectar_destino()

    # try except pq pode ter erros e tal, ai executa td de uma vez
    try:
        # limpa as tabelas antes de comecar a carga
        limpar_banco_destino(conn_destino)

        # guarda todas as conversões de pk num dicionario pra facilitar passar pro pandas
        mapas = {
            # esse mapa aqui é um depara pra carregar as tabelas
            'tipo': carregar_dim_tipo(conn_destino),
            'categoria': carregar_dim_categoria(conn_origem, conn_destino),
            'funcionario': carregar_dim_funcionario(conn_origem, conn_destino),
            'cliente': carregar_dim_cliente(conn_origem, conn_destino),
            'loja': carregar_dim_loja(conn_origem, conn_destino),
            'canal': carregar_dim_canal(conn_destino),
            'mes': carregar_dim_mes(conn_destino),
            'ano': carregar_dim_ano(conn_origem, conn_destino)
        }

        # executa tudo
        processar_fato_pandas(conn_origem, conn_destino, mapas)

        print("Carga concluída com sucesso.")
    except Exception as e:
        conn_destino.rollback()
        print(f"Erro na carga, rollback aplicado: {e}")
    finally:
        conn_origem.close()
        conn_destino.close()

if __name__ == "__main__":
    main()