-- DDL tabelas de dimensão
CREATE TABLE tipo (
	pk_tipo INT AUTO_INCREMENT,
	nome_tipo VARCHAR(20) NOT NULL,
	PRIMARY KEY (pk_tipo)
);

CREATE TABLE cliente (
	pk_cliente INT AUTO_INCREMENT,
	nome VARCHAR(255) NOT NULL,
	PRIMARY KEY (pk_cliente)
);

CREATE TABLE loja (
	pk_loja INT AUTO_INCREMENT,
	cidade VARCHAR(255) NOT NULL,
	uf VARCHAR(2),
	PRIMARY KEY (pk_loja)
);

CREATE TABLE mes (
	pk_mes INT AUTO_INCREMENT,
	nome_mes VARCHAR(20) NOT NULL,
	PRIMARY KEY (pk_mes)
);

CREATE TABLE categoria (
	pk_categoria INT AUTO_INCREMENT,
	nome_categoria VARCHAR(255) NOT NULL,
	PRIMARY KEY (pk_categoria)
);

CREATE TABLE funcionario (
	pk_funcionario INT AUTO_INCREMENT,
	nome_completo VARCHAR(255) NOT NULL,
	cargo VARCHAR(255),
	PRIMARY KEY (pk_funcionario)
);

CREATE TABLE canal (
	pk_canal INT AUTO_INCREMENT,
	nome_canal VARCHAR(20) NOT NULL,
	PRIMARY KEY (pk_canal)
);

CREATE TABLE ano (
	pk_ano INT,
	PRIMARY KEY (pk_ano)
);

-- DDL tabela fato_venda
CREATE TABLE fato_venda (
	fk_tipo INT,
	fk_categoria INT,
	fk_funcionario INT,
	fk_cliente INT,
	fk_loja INT,
	fk_canal INT,
	fk_mes INT,
	fk_ano INT,
	quantidade INT,
	valor DECIMAL(12, 2),
	
	CONSTRAINT fk_fato_tipo FOREIGN KEY (fk_tipo) REFERENCES tipo(pk_tipo),
	CONSTRAINT fk_fato_categoria FOREIGN KEY (fk_categoria) REFERENCES categoria(pk_categoria),
	CONSTRAINT fk_fato_funcionario FOREIGN KEY (fk_funcionario) REFERENCES funcionario(pk_funcionario),
	CONSTRAINT fk_fato_cliente FOREIGN KEY (fk_cliente) REFERENCES cliente(pk_cliente),
	CONSTRAINT fk_fato_loja FOREIGN KEY (fk_loja) REFERENCES loja(pk_loja),
	CONSTRAINT fk_fato_canal FOREIGN KEY (fk_canal) REFERENCES canal(pk_canal),
	CONSTRAINT fk_fato_mes FOREIGN KEY (fk_mes) REFERENCES mes(pk_mes),
	CONSTRAINT fk_fato_ano FOREIGN KEY (fk_ano) REFERENCES ano(pk_ano)
);

CREATE INDEX idx_fato_venda_tipo ON fato_venda(fk_tipo);
CREATE INDEX idx_fato_venda_categoria ON fato_venda(fk_categoria);
CREATE INDEX idx_fato_venda_funcionario ON fato_venda(fk_funcionario);
CREATE INDEX idx_fato_venda_cliente ON fato_venda(fk_cliente);
CREATE INDEX idx_fato_venda_loja ON fato_venda(fk_loja);
CREATE INDEX idx_fato_venda_canal ON fato_venda(fk_canal);
CREATE INDEX idx_fato_venda_mes ON fato_venda(fk_mes);
CREATE INDEX idx_fato_venda_ano ON fato_venda(fk_anoo);