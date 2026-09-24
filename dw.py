"""
Requisitos:
    pip install pyodbc pymysql
"""

import pyodbc
import pymysql

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
    # cursor p fazer as consultas no sqlserver
    cur_o = conn_origem.cursor()
    cur_o.execute("SELECT tb013_cod_categoria, tb013_descricao FROM tb013_categorias")
    linhas = cur_o.fetchall()

    # cursor p fazer os inserts no mysql
    cur_d = conn_dest.cursor()
    # esse mapa é p criar as chaves auto incrementais la no mysql
    mapa = {}
    for cod, descricao in linhas:
        cur_d.execute("INSERT INTO categoria (nome_categoria) VALUES (%s)", (descricao,))
        # captura o id criado la no mysql
        mapa[cod] = cur_d.lastrowid
    # salva para efetuar realmente apenas se nao tiver erros na execucao
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
    # cadastra fixamente os canais de loja fisica e virtual
    cur = conn_dest.cursor()
    mapa = {}
    for nome in ["Loja Física", "Loja Virtual"]:
        cur.execute("INSERT INTO canal (nome_canal) VALUES (%s)", (nome,))
        mapa[nome] = cur.lastrowid
    conn_dest.commit()
    return mapa


def carregar_dim_mes(conn_dest):
    # carrega fixamente o nome dos meses
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
    cur_o.execute("SELECT DISTINCT YEAR(tb010_012_data) FROM tb010_012_vendas") # so tem 2025
    anos = [linha[0] for linha in cur_o.fetchall()]

    cur_d = conn_dest.cursor()
    mapa = {}
    for ano in anos:
        cur_d.execute("INSERT INTO ano (pk_ano) VALUES (%s)", (ano,))
        mapa[ano] = ano  # aqui a pk é o próprio ano
    conn_dest.commit()
    return mapa



# ----------------------------------------------------------------------
# 3. carregando os dados na tabela fato
#   3.1 agrupa e soma com base no que a pergunta quer
#   3.2 insere com base nos ids mapeados nos mapas criados na etapa 2
#   3.3 grava tudo isso na fato_venda
# ----------------------------------------------------------------------

def carregar_fato_tipo_categoria(conn_origem, conn_dest, mapa_tipo, mapa_categoria):
    """Pergunta 1: quantidade de vendas por tipo e categoria."""
    cur_o = conn_origem.cursor()
    cur_o.execute("""
        SELECT sub.tipo, p.tb013_cod_categoria,
               SUM(v.tb010_012_quantidade) AS qtd,
               SUM(v.tb010_012_quantidade * v.tb010_012_valor_unitario) AS valor
        FROM tb010_012_vendas v
        JOIN tb012_produtos p ON v.tb012_cod_produto = p.tb012_cod_produto
        JOIN (
            SELECT tb012_cod_produto AS cod, 'Alimento' AS tipo FROM tb014_prd_alimentos
            UNION ALL
            SELECT tb012_cod_produto, 'Eletro' FROM tb015_prd_eletros
            UNION ALL
            SELECT tb012_cod_produto, 'Vestuario' FROM tb016_prd_vestuarios
        ) sub ON p.tb012_cod_produto = sub.cod
        GROUP BY sub.tipo, p.tb013_cod_categoria
    """)
    linhas = cur_o.fetchall()

    cur_d = conn_dest.cursor()
    for tipo, cod_categoria, qtd, valor in linhas:
        cur_d.execute("""
            INSERT INTO fato_venda
                (fk_tipo, fk_categoria, fk_funcionario, fk_cliente,
                fk_loja, fk_canal, fk_mes, fk_ano, quantidade, valor)
            VALUES (%s, %s, NULL, NULL, NULL, NULL, NULL, NULL, %s, %s)
        """, (mapa_tipo[tipo], mapa_categoria[cod_categoria], qtd, valor))
    conn_dest.commit()
    print(f"[tipo+categoria] {len(linhas)} linhas inseridas")


def carregar_fato_funcionario_mes_ano(conn_origem, conn_dest, mapa_funcionario, mapa_mes, mapa_ano):
    """Pergunta 2: valor das vendas por funcionário, hierárquico por tempo."""
    cur_o = conn_origem.cursor()
    cur_o.execute("""
        SELECT v.tb005_matricula, MONTH(v.tb010_012_data), YEAR(v.tb010_012_data),
               SUM(v.tb010_012_quantidade) AS qtd,
               SUM(v.tb010_012_quantidade * v.tb010_012_valor_unitario) AS valor
        FROM tb010_012_vendas v
        GROUP BY v.tb005_matricula, MONTH(v.tb010_012_data), YEAR(v.tb010_012_data)
    """)
    linhas = cur_o.fetchall()

    cur_d = conn_dest.cursor()
    for matricula, mes, ano, qtd, valor in linhas:
        cur_d.execute("""
            INSERT INTO fato_venda
                (fk_tipo, fk_categoria, fk_funcionario, fk_cliente,
                fk_loja, fk_canal, fk_mes, fk_ano, quantidade, valor)
            VALUES (NULL, NULL, %s, NULL, NULL, NULL, %s, %s, %s, %s)
        """, (mapa_funcionario[matricula], mapa_mes[mes], mapa_ano[ano], qtd, valor))
    conn_dest.commit()
    print(f"[funcionario+mes+ano] {len(linhas)} linhas inseridas")

def carregar_fato_funcionario(conn_origem, conn_dest, mapa_funcionario):
    """Pergunta 3: Volume total por funcionário"""
    cur_o = conn_origem.cursor()
    cur_o.execute("""
        SELECT v.tb005_matricula,
               SUM(v.tb010_012_quantidade) AS qtd,
               SUM(v.tb010_012_quantidade * v.tb010_012_valor_unitario) AS valor
        FROM tb010_012_vendas v
        GROUP BY v.tb005_matricula
    """)
    linhas = cur_o.fetchall()

    cur_d = conn_dest.cursor()
    for matricula, qtd, valor in linhas:
        cur_d.execute("""
            INSERT INTO fato_venda
                (fk_tipo, fk_categoria, fk_funcionario, fk_cliente,
                 fk_loja, fk_canal, fk_mes, fk_ano, quantidade, valor)
            VALUES (NULL, NULL, %s, NULL, NULL, NULL, NULL, NULL, %s, %s)
        """, (mapa_funcionario[matricula], qtd, valor))
    conn_dest.commit()
    print(f"[funcionario] {len(linhas)} linhas inseridas")

def carregar_fato_funcionario_loja(conn_origem, conn_dest, mapa_funcionario, mapa_loja):
    """Pergunta 4: Atendimentos por funcionário e localidade."""
    cur_o = conn_origem.cursor()
    cur_o.execute("""
        SELECT v.tb005_matricula, f.tb004_cod_loja,
               SUM(v.tb010_012_quantidade) AS qtd,
               SUM(v.tb010_012_quantidade * v.tb010_012_valor_unitario) AS valor
        FROM tb010_012_vendas v
        JOIN tb005_funcionarios f ON v.tb005_matricula = f.tb005_matricula
        GROUP BY v.tb005_matricula, f.tb004_cod_loja
    """)
    linhas = cur_o.fetchall()

    cur_d = conn_dest.cursor()
    for matricula, cod_loja, qtd, valor in linhas:
        cur_d.execute("""
            INSERT INTO fato_venda
                (fk_tipo, fk_categoria, fk_funcionario, fk_cliente,
                fk_loja, fk_canal, fk_mes, fk_ano, quantidade, valor)
            VALUES (NULL, NULL, %s, NULL, %s, NULL, NULL, NULL, %s, %s)
        """, (mapa_funcionario[matricula], mapa_loja[cod_loja], qtd, valor))
    conn_dest.commit()
    print(f"[funcionario+loja] {len(linhas)} linhas inseridas")


def carregar_fato_cliente_mes_ano(conn_origem, conn_dest, mapa_cliente, mapa_mes, mapa_ano):
    """
    Pergunta 5: Valor das ultimas vendas realizadas por cliente.
    Agrega as vendas por Cliente, Mes e Ano.
    """
    cur_o = conn_origem.cursor()
    cur_o.execute("""
        SELECT v.tb010_cpf, MONTH(v.tb010_012_data), YEAR(v.tb010_012_data),
               SUM(v.tb010_012_quantidade) AS qtd,
               SUM(v.tb010_012_quantidade * v.tb010_012_valor_unitario) AS valor
        FROM tb010_012_vendas v
        GROUP BY v.tb010_cpf, MONTH(v.tb010_012_data), YEAR(v.tb010_012_data)
    """)
    linhas = cur_o.fetchall()

    cur_d = conn_dest.cursor()
    for cpf, mes, ano, qtd, valor in linhas:
        cur_d.execute("""
            INSERT INTO fato_venda
                (fk_tipo, fk_categoria, fk_funcionario, fk_cliente,
                fk_loja, fk_canal, fk_mes, fk_ano, quantidade, valor)
            VALUES (NULL, NULL, NULL, %s, NULL, NULL, %s, %s, %s, %s)
        """, (mapa_cliente[cpf], mapa_mes[mes], mapa_ano[ano], qtd, valor))
    conn_dest.commit()
    print(f"[cliente+mes+ano] {len(linhas)} linhas inseridas")


def carregar_fato_cliente_canal_mes_ano(conn_origem, conn_dest, mapa_cliente, mapa_canal, mapa_mes, mapa_ano):
    """
    Pergunta 6: Clientes que mais compraram na loja virtual com valor acumulado por período.
    Agrega as vendas por Cliente, Mês e Ano.
    """
    cur_o = conn_origem.cursor()
    
    cur_o.execute("""
        SELECT 
            sub.tb010_cpf,
            sub.canal,
            sub.mes,
            sub.ano,
            SUM(sub.qtd) AS qtd,
            SUM(sub.valor) AS valor
        FROM (
            SELECT 
                v.tb010_cpf,
                CASE 
                    WHEN l.tb010_cpf IS NOT NULL THEN 'Loja Virtual' 
                    ELSE 'Loja Física' 
                END AS canal,
                MONTH(v.tb010_012_data) AS mes,
                YEAR(v.tb010_012_data) AS ano,
                v.tb010_012_quantidade AS qtd,
                (v.tb010_012_quantidade * v.tb010_012_valor_unitario) AS valor
            FROM tb010_012_vendas v
            LEFT JOIN (SELECT DISTINCT tb010_cpf FROM tb011_logins) l 
                ON v.tb010_cpf = l.tb010_cpf
        ) sub
        GROUP BY sub.tb010_cpf, sub.canal, sub.mes, sub.ano
    """)
    linhas = cur_o.fetchall()

    cur_d = conn_dest.cursor()
    for cpf, canal, mes, ano, qtd, valor in linhas:
        cur_d.execute("""
            INSERT INTO fato_venda
                (fk_tipo, fk_categoria, fk_funcionario, fk_cliente,
                fk_loja, fk_canal, fk_mes, fk_ano, quantidade, valor)
            VALUES (NULL, NULL, NULL, %s, NULL, %s, %s, %s, %s, %s)
        """, (mapa_cliente[cpf], mapa_canal[canal], mapa_mes[mes], mapa_ano[ano], qtd, valor))
    conn_dest.commit()
    print(f"[cliente+canal+mes+ano] {len(linhas)} linhas inseridas")

# ----------------------------------------------------------------------
# 4. orquestração
#   4.1 conecta com o banco
#   4.2 faz a carga nas dimensoes
#   4.3 faz a carga na fato com mapas e tal
#   4.4  finaliza e fecha as conexoes co m o banco
# ----------------------------------------------------------------------

def main():
    conn_origem = conectar_origem()
    conn_destino = conectar_destino()

    # try except pq pode ter erros e tal, ai executa td de uma vez
    try:
        mapa_tipo = carregar_dim_tipo(conn_destino)
        mapa_categoria = carregar_dim_categoria(conn_origem, conn_destino)
        mapa_funcionario = carregar_dim_funcionario(conn_origem, conn_destino)
        mapa_cliente = carregar_dim_cliente(conn_origem, conn_destino)
        mapa_loja = carregar_dim_loja(conn_origem, conn_destino)
        mapa_canal = carregar_dim_canal(conn_destino)
        mapa_mes = carregar_dim_mes(conn_destino)
        mapa_ano = carregar_dim_ano(conn_origem, conn_destino)

        carregar_fato_tipo_categoria(conn_origem, conn_destino, mapa_tipo, mapa_categoria)
        carregar_fato_funcionario_mes_ano(conn_origem, conn_destino, mapa_funcionario, mapa_mes, mapa_ano)
        carregar_fato_funcionario(conn_origem, conn_destino, mapa_funcionario)
        carregar_fato_funcionario_loja(conn_origem, conn_destino, mapa_funcionario, mapa_loja)
        carregar_fato_cliente_mes_ano(conn_origem, conn_destino, mapa_cliente, mapa_mes, mapa_ano)
        carregar_fato_cliente_canal_mes_ano(conn_origem, conn_destino, mapa_cliente, mapa_canal, mapa_mes, mapa_ano)

        print("Carga concluída com sucesso.")
    except Exception as e:
        conn_destino.rollback()
        print(f"Erro na carga, rollback aplicado: {e}")
    finally:
        conn_origem.close()
        conn_destino.close()


if __name__ == "__main__":
    main()