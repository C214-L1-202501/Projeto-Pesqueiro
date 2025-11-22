from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional # <--- IMPORT VITAL
from App.schemas.item import ItemResponse # <--- Importa o esquema do item

class ComandaBase(BaseModel):
    cliente_id: int

class ComandaCreate(ComandaBase):
    pass

class ComandaResponse(ComandaBase):
    id: int
    status: str
    valor_total: float
    criado_em: datetime
    
    # Campo que vai receber a lista de itens do relacionamento no Model
    itens: Optional[List[ItemResponse]] = None # <--- O CAMPO QUE O FRONT PRECISA

    class Config:
        from_attributes = True