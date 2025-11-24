from fastapi.testclient import TestClient
from App.api.main import app
from App.db.connection import Base, engine
import pytest

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_criar_cliente():
    r = client.post("/clientes", json={
        "nome": "João",
        "cpf": "11122233344",
        "telefone": "99999-0000",
        "email": "joao@test.com"
    })
    assert r.status_code == 200
    assert r.json()["cpf"] == "11122233344"


def test_cliente_cpf_duplicado():
    r = client.post("/clientes", json={
        "nome": "Duplicado",
        "cpf": "11122233344",
        "telefone": "99999-1111",
        "email": "dup@test.com"
    })
    assert r.status_code == 400


def test_criar_comanda():
    r = client.post("/comandas?cliente_id=1")
    assert r.status_code == 200
    assert r.json()["cliente_id"] == 1


def test_adicionar_item():
    r = client.post("/comandas/1/itens", json={
        "nome_produto": "Coca-Cola",
        "quantidade": 2,
        "preco_unitario": 5.0
    })
    assert r.status_code == 200
    assert r.json()["valor_total"] == 10.0


def test_valor_total_comanda():
    r = client.get("/comandas/1")
    assert r.status_code == 200
    assert r.json()["valor_total"] == 10.0


def test_nao_pode_deletar_comanda_com_itens():
    r = client.delete("/comandas/1")
    assert r.status_code == 400


def test_segunda_comanda_mesmo_cliente():
    r = client.post("/comandas?cliente_id=1")
    assert r.status_code == 200
    assert r.json()["status"] == "ABERTA"


def test_cliente_invalido():
    r = client.post("/clientes", json={
        "nome": "",
        "cpf": "",
        "telefone": "",
        "email": ""
    })
    assert r.status_code == 422


def test_listar_comandas():
    r = client.get("/comandas")
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_reset_db():
    r = client.post("/admin/reset-db")
    assert r.status_code == 200

    r2 = client.get("/clientes")
    assert r2.status_code == 200
    assert len(r2.json()) == 0
