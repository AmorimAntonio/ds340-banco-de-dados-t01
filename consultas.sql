USE dw_vendas;

-- ======================================================================
-- pergunta 1 - quantidade e valor de vendas por tipo e categoria
-- ======================================================================
SELECT 
    t.nome_tipo,
    c.nome_categoria,
    f.quantidade,
    f.valor
FROM fato_venda f
JOIN tipo t ON f.fk_tipo = t.pk_tipo
JOIN categoria c ON f.fk_categoria = c.pk_categoria
WHERE f.fk_tipo IS NOT NULL 
  AND f.fk_categoria IS NOT NULL 
  AND f.fk_funcionario IS NULL 
  AND f.fk_cliente IS NULL 
  AND f.fk_loja IS NULL 
  AND f.fk_canal IS NULL 
  AND f.fk_mes IS NULL 
  AND f.fk_ano IS NULL;


-- ======================================================================
-- pergunta 2 - valor das vendas por funcionário, hierárquico por tempo (mês e ano)
-- ======================================================================
SELECT 
    fu.nome_completo AS funcionario,
    m.nome_mes,
    a.pk_ano AS ano,
    f.quantidade,
    f.valor
FROM fato_venda f
JOIN funcionario fu ON f.fk_funcionario = fu.pk_funcionario
JOIN mes m ON f.fk_mes = m.pk_mes
JOIN ano a ON f.fk_ano = a.pk_ano
WHERE f.fk_funcionario IS NOT NULL 
  AND f.fk_mes IS NOT NULL 
  AND f.fk_ano IS NOT NULL 
  AND f.fk_tipo IS NULL 
  AND f.fk_categoria IS NULL 
  AND f.fk_cliente IS NULL 
  AND f.fk_loja IS NULL 
  AND f.fk_canal IS NULL;


-- ======================================================================
-- pergunta 3 - volume total por funcionário
-- ======================================================================
SELECT 
    fu.nome_completo AS funcionario,
    f.quantidade,
    f.valor
FROM fato_venda f
JOIN funcionario fu ON f.fk_funcionario = fu.pk_funcionario
WHERE f.fk_funcionario IS NOT NULL 
  AND f.fk_tipo IS NULL 
  AND f.fk_categoria IS NULL 
  AND f.fk_cliente IS NULL 
  AND f.fk_loja IS NULL 
  AND f.fk_canal IS NULL 
  AND f.fk_mes IS NULL 
  AND f.fk_ano IS NULL;


-- ======================================================================
-- pergunta 4 - atendimentos por funcionário e localidade (loja)
-- ======================================================================
SELECT 
    fu.nome_completo AS funcionario,
    l.cidade,
    l.uf,
    f.quantidade,
    f.valor
FROM fato_venda f
JOIN funcionario fu ON f.fk_funcionario = fu.pk_funcionario
JOIN loja l ON f.fk_loja = l.pk_loja
WHERE f.fk_funcionario IS NOT NULL 
  AND f.fk_loja IS NOT NULL 
  AND f.fk_tipo IS NULL 
  AND f.fk_categoria IS NULL 
  AND f.fk_cliente IS NULL 
  AND f.fk_canal IS NULL 
  AND f.fk_mes IS NULL 
  AND f.fk_ano IS NULL;


-- ======================================================================
-- pergunta 5 - valor das vendas realizadas por cliente por período (mês e ano)
-- ======================================================================
SELECT 
    cl.nome AS cliente,
    m.nome_mes,
    a.pk_ano AS ano,
    f.quantidade,
    f.valor
FROM fato_venda f
JOIN cliente cl ON f.fk_cliente = cl.pk_cliente
JOIN mes m ON f.fk_mes = m.pk_mes
JOIN ano a ON f.fk_ano = a.pk_ano
WHERE f.fk_cliente IS NOT NULL 
  AND f.fk_mes IS NOT NULL 
  AND f.fk_ano IS NOT NULL 
  AND f.fk_tipo IS NULL 
  AND f.fk_categoria IS NULL 
  AND f.fk_funcionario IS NULL 
  AND f.fk_loja IS NULL 
  AND f.fk_canal IS NULL;


-- ======================================================================
-- pergunta 6 - vendas por cliente, canal e período (mês e ano)
-- ======================================================================
SELECT 
    cl.nome AS cliente,
    ca.nome_canal AS canal,
    m.nome_mes,
    a.pk_ano AS ano,
    f.quantidade,
    f.valor
FROM fato_venda f
JOIN cliente cl ON f.fk_cliente = cl.pk_cliente
JOIN canal ca ON f.fk_canal = ca.pk_canal
JOIN mes m ON f.fk_mes = m.pk_mes
JOIN ano a ON f.fk_ano = a.pk_ano
WHERE f.fk_cliente IS NOT NULL 
  AND f.fk_canal IS NOT NULL 
  AND f.fk_mes IS NOT NULL 
  AND f.fk_ano IS NOT NULL 
  AND f.fk_tipo IS NULL 
  AND f.fk_categoria IS NULL 
  AND f.fk_funcionario IS NULL 
  AND f.fk_loja IS NULL;