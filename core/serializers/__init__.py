from .user import UserRegistrationSerializer, UserSerializer
from .produto import (
    ProdutoAlterarPrecoSerializer,
    ProdutoListSerializer,
    ProdutoRetrieveSerializer,
    ProdutoSerializer,
)
from .categoria import CategoriaSerializer
from .marca import MarcaSerializer
from .compra import (
    CompraCreateUpdateSerializer,
    CompraSerializer,
    ItensCompraCreateUpdateSerializer,
    ItensCompraSerializer,
    ItensCompraListSerializer,
    CompraListSerializer,
)
