from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from App.db.connection import Base

class Comanda(Base):
    __tablename__ = "comandas"

    # --- COLUNAS ESSENCIAIS (RESTAURADAS) ---
    id = Column(Integer, primary_key=True, index=True) # A CHAVE PRIMÁRIA QUE ESTAVA FALTANDO!
    cliente_id = Column(Integer, ForeignKey("clientes.id")) 
    
    status = Column(String, default="ABERTA") 
    valor_total = Column(Float, default=0.0)  
    criado_em = Column(DateTime(timezone=True), server_default=func.now()) 
    # ----------------------------------------
    
    # Relacionamentos
    itens = relationship("ItemComanda")
    cliente = relationship("Cliente")