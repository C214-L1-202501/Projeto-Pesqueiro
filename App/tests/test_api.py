from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from App.api.main import app, get_db
from App.db.connection import Base

# 1. Configura um Banco de Dados de Teste (Na memória, para não sujar o real)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria as tabelas no banco de teste
Base.metadata.create_all(bind=engine)

# Substitui o banco real pelo banco de teste
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# --- OS TESTES COMEÇAM AQUI ---

def test_fluxo_completo_pesqueiro():
    """
    Teste de Integração:
    1. Cria Cliente
    2. Abre Comanda
    3. Lança Item
    4. Verifica se o total foi calculado certo
    """
    
    # 1. Cadastrar Cliente
    response = client.post("/clientes", json={"nome": "Tester", "cpf": "99988877700", "telefone": "", "email": ""})
    assert response.status_code == 200
    data_cliente = response.json()
    cliente_id = data_cliente["id"]
    
    # 2. Abrir Comanda
    response = client.post("/comandas", json={"cliente_id": cliente_id})
    assert response.status_code == 200
    data_comanda = response.json()
    comanda_id = data_comanda["id"]
    assert data_comanda["valor_total"] == 0  # Tem que começar zerada
    
    # 3. Lançar Item (2 Cervejas a R$ 10,00)
    item_payload = {
        "comanda_id": comanda_id,
        "nome_produto": "Cerveja Teste",
        "quantidade": 2,
        "preco_unitario": 10.0
    }
    response = client.post("/itens", json=item_payload)
    assert response.status_code == 200
    
    # 4. A PROVA FINAL: Consultar se o valor subiu para 20.0
    response = client.get(f"/comandas/{comanda_id}")
    assert response.status_code == 200
    dados_finais = response.json()
    
    # O teste falha se o valor não for 20.0
    assert dados_finais["valor_total"] == 20.0

@pytest.fixture(scope="module")
def client():
    client = TestClient(app)
    database.Base.metadata.create_all(bind=database.engine)
    yield client
    database.Base.metadata.drop_all(bind=database.engine)


def test_criar_cliente_sucesso(client):
    # Teste verdadeiro: criar cliente com dados válidos
    payload = {"nome": "João", "cpf": "12345678901"}
    response = client.post("/clientes/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "João"
    assert data["cpf"] == "12345678901"


def test_criar_cliente_cpf_duplicado(client):
    # Teste falso: tentar criar cliente com CPF já cadastrado
    payload = {"nome": "Maria", "cpf": "12345678901"}  # mesmo CPF do João
    response = client.post("/clientes/", json=payload)
    assert response.status_code == 400 or response.status_code == 409 
    assert "cpf" in response.json()["detail"].lower()


def test_criar_comanda_sucesso(client):
    # Teste verdadeiro: abrir uma comanda para cliente existente
    # Primeiro, pegar o cliente criado
    response_cliente = client.post("/clientes/", json={"nome": "Pedro", "cpf": "98765432100"})
    cliente_id = response_cliente.json()["id"]

    payload = {"cliente_id": cliente_id}
    response = client.post("/comandas/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["cliente_id"] == cliente_id
    assert data["valor_total"] == 0  # comanda inicial sem itens


def test_criar_duas_comandas_para_mesmo_cliente_aberta(client):
    # Teste falso: não permitir duas comandas abertas para o mesmo cliente
    # Usar cliente já criado 
    # Tentar abrir uma segunda comanda sem fechar a primeira
    cliente_id = 3  
    payload = {"cliente_id": cliente_id}
    response = client.post("/comandas/", json=payload)
    # Deve dar erro 
    assert response.status_code == 400
    assert "já existe" in response.json()["detail"].lower()


def test_adicionar_item_sucesso(client):
    # Teste verdadeiro: adicionar item a uma comanda aberta
    response_cliente = client.post("/clientes/", json={"nome": "Ana", "cpf": "11122233344"})
    cliente_id = response_cliente.json()["id"]
    response_comanda = client.post("/comandas/", json={"cliente_id": cliente_id})
    comanda_id = response_comanda.json()["id"]

    # Adicionar item
    item_payload = {"comanda_id": comanda_id, "descricao": "Refri", "preco": 5.50}
    response_item = client.post("/itens/", json=item_payload)
    assert response_item.status_code == 201
    data = response_item.json()
    assert data["descricao"] == "Refri"
    assert data["preco"] == 5.50

    # Verificar se valor_total da comanda foi atualizado
    response_comanda2 = client.get(f"/comandas/{comanda_id}")
    comanda_data = response_comanda2.json()
    assert comanda_data["valor_total"] == pytest.approx(5.50)


def test_adicionar_item_comanda_invalida(client):
    # Teste falso: adicionar item para uma comanda que não existe
    item_payload = {"comanda_id": 9999, "descricao": "Cerveja", "preco": 8.00}
    response = client.post("/itens/", json=item_payload)
    assert response.status_code == 404
    assert "comanda" in response.json()["detail"].lower()


def test_fechar_comanda_sucesso(client):
    # Teste verdadeiro: fechar corretamente uma comanda e não permitir novos itens
    response_cliente = client.post("/clientes/", json={"nome": "Lucas", "cpf": "55566677788"})
    cliente_id = response_cliente.json()["id"]
    response_comanda = client.post("/comandas/", json={"cliente_id": cliente_id})
    comanda_id = response_comanda.json()["id"]

    # Adicionar item
    client.post("/itens/", json={"comanda_id": comanda_id, "descricao": "Suco", "preco": 4.00})

    # Fechar comanda
    response_close = client.put(f"/comandas/{comanda_id}/fechar")
    assert response_close.status_code == 200
    data_close = response_close.json()
    assert data_close["aberta"] is False

    # Tentar adicionar item após fechar — deve falhar
    response_item = client.post("/itens/", json={"comanda_id": comanda_id, "descricao": "Água", "preco": 3.00})
    assert response_item.status_code == 400 or response_item.status_code == 403
    assert "fechada" in response_item.json()["detail"].lower()


def test_get_comandas_por_cliente(client):
    # Teste verdadeiro: listar todas as comandas de um cliente
    response_cliente = client.post("/clientes/", json={"nome": "Beatriz", "cpf": "22233344455"})
    cid = response_cliente.json()["id"]
    client.post("/comandas/", json={"cliente_id": cid})
    client.post("/comandas/", json={"cliente_id": cid})

    response = client.get(f"/clientes/{cid}/comandas")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # pelo menos 2 comandas


def test_excluir_item_sucesso(client):
    # Teste verdadeiro: excluir um item e verificar se o valor total da comanda diminui
    response_cliente = client.post("/clientes/", json={"nome": "Clara", "cpf": "33344455566"})
    cid = response_cliente.json()["id"]
    response_comanda = client.post("/comandas/", json={"cliente_id": cid})
    comanda_id = response_comanda.json()["id"]
    # dois itens
    r1 = client.post("/itens/", json={"comanda_id": comanda_id, "descricao": "Pizza", "preco": 20.0})
    r2 = client.post("/itens/", json={"comanda_id": comanda_id, "descricao": "Refrigerante", "preco": 5.0})
    item1_id = r1.json()["id"]
    item2_id = r2.json()["id"]

    # valor total deve ser 25
    resp = client.get(f"/comandas/{comanda_id}")
    assert resp.json()["valor_total"] == pytest.approx(25.0)

    # deletar item 1
    resp_del = client.delete(f"/itens/{item1_id}")
    assert resp_del.status_code == 200

    # buscar comanda novamente com novo valor
    resp2 = client.get(f"/comandas/{comanda_id}")
    assert resp2.json()["valor_total"] == pytest.approx(5.0)


def test_excluir_comanda_sucesso(client):
    # Teste verdadeiro: excluir uma comanda
    response_cliente = client.post("/clientes/", json={"nome": "Diego", "cpf": "77788899900"})
    cid = response_cliente.json()["id"]
    response_comanda = client.post("/comandas/", json={"cliente_id": cid})
    comanda_id = response_comanda.json()["id"]

    resp_del = client.delete(f"/comandas/{comanda_id}")
    assert resp_del.status_code == 200

    # depois de deletar, buscar deve dar 404
    resp_get = client.get(f"/comandas/{comanda_id}")
    assert resp_get.status_code == 404


def test_valor_total_com_multiple_itens(client):
    # Teste verdadeiro: adicionar vários itens e verificar total acumulado
    response_cliente = client.post("/clientes/", json={"nome": "Eva", "cpf": "44455566677"})
    cid = response_cliente.json()["id"]
    response_comanda = client.post("/comandas/", json={"cliente_id": cid})
    comanda_id = response_comanda.json()["id"]

    client.post("/itens/", json={"comanda_id": comanda_id, "descricao": "Espaguete", "preco": 12.0})
    client.post("/itens/", json={"comanda_id": comanda_id, "descricao": "Salada", "preco": 6.5})
    client.post("/itens/", json={"comanda_id": comanda_id, "descricao": "Sobremesa", "preco": 4.0})

    resp = client.get(f"/comandas/{comanda_id}")
    assert resp.json()["valor_total"] == pytest.approx(22.5)


def test_fechar_comanda_inexistente(client):
    # Teste falso: tentar fechar uma comanda que não existe
    resp = client.put("/comandas/9999/fechar")
    assert resp.status_code == 404
    assert "não encontrada" in resp.json()["detail"].lower()


def test_cliente_nao_existente_comanda(client):
    # Teste falso: criar comanda para cliente inexistente
    payload = {"cliente_id": 9999}
    resp = client.post("/comandas/", json=payload)
    assert resp.status_code == 404
    assert "cliente" in resp.json()["detail"].lower()


def test_item_preco_negativo(client):
    # Teste falso: não permitir item com preço negativo
    response_cliente = client.post("/clientes/", json={"nome": "Felipe", "cpf": "88899900011"})
    cid = response_cliente.json()["id"]
    response_comanda = client.post("/comandas/", json={"cliente_id": cid})
    comanda_id = response_comanda.json()["id"]

    item_payload = {"comanda_id": comanda_id, "descricao": "Negativo", "preco": -5.0}
    resp = client.post("/itens/", json=item_payload)
    assert resp.status_code == 400
    assert "preço" in resp.json()["detail"].lower()


def test_buscar_cliente_sucesso(client):
    # Teste verdadeiro: buscar cliente por id
    response_cliente = client.post("/clientes/", json={"nome": "Gabriela", "cpf": "99900011122"})
    cid = response_cliente.json()["id"]
    resp = client.get(f"/clientes/{cid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["nome"] == "Gabriela"
    assert data["cpf"] == "99900011122"


def test_buscar_cliente_inexistente(client):
    # Teste falso: buscar cliente que não existe
    resp = client.get("/clientes/9999")
    assert resp.status_code == 404
    assert "não encontrado" in resp.json()["detail"].lower()
