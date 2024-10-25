from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, conint, validator
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi.middleware.cors import CORSMiddleware


url = "postgresql+psycopg2://postgres:j2g9n4@localhost:5432/usuarios"


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base = declarative_base()


class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    idade = Column(Integer)


class UsuarioDeletado(Base):
    __tablename__ = "usuarios_deletados"
    id = Column(Integer, primary_key=True, index=True)


class UsuarioCreate(BaseModel):
    nome: str
    email: str
    idade: conint(ge=0)

    @validator('email')
    def validate_email(cls, email):
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Formato email errado")
        return email


engine = create_engine(url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    """Retorna uma mensagem de boas-vindas."""
    return {"message": "Bem-vindo à API FastAPI!"}

@app.get('/usuarios/')
def lista_usuarios(db: Session = Depends(get_db)):
    """Lista todos os usuários cadastrados."""
    return db.query(Usuario).all()

@app.get("/usuarios/{ID_Usuario}")
def verificar_usuario(ID_Usuario: int, db: Session = Depends(get_db)):
    """Verifica e retorna um usuário específico pelo ID."""
    usuario = db.query(Usuario).filter(Usuario.id == ID_Usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario

@app.post('/usuarios/', status_code=201)
def criar_usuario(user: UsuarioCreate, db: Session = Depends(get_db)):
    """Cria um novo usuário e reutiliza o ID de um usuário deletado, se disponível."""
    id_deletado = db.query(UsuarioDeletado).first()
    if id_deletado:
        novo_usuario = Usuario(id=id_deletado.id, **user.dict())
        db.delete(id_deletado)
    else:
        novo_usuario = Usuario(**user.dict())
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return novo_usuario

@app.put('/usuarios/{ID_Usuario}', status_code=200)
def atualizar_usuario(ID_Usuario: int, usuario: UsuarioCreate, db: Session = Depends(get_db)):
    """Atualiza os dados de um usuário existente."""
    existing_user = db.query(Usuario).filter(Usuario.id == ID_Usuario).first()
    if not existing_user:
        raise HTTPException(status_code=404, detail=f'Usuário com ID {ID_Usuario} não encontrado.')

    for attr, value in usuario.dict().items():
        setattr(existing_user, attr, value)

    db.commit()
    db.refresh(existing_user)
    return existing_user

@app.delete('/usuarios/{ID_Usuario}', status_code=200)
def delete_usuario(ID_Usuario: int, db: Session = Depends(get_db)):
    """Deleta um usuário pelo ID e retorna uma mensagem de confirmação."""
    usuario = db.query(Usuario).filter(Usuario.id == ID_Usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail=f'Usuário com ID {ID_Usuario} não encontrado.')

    db.delete(usuario)
    db.commit()
    return {"detail": "Usuário deletado."}
