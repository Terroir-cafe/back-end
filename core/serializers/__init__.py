from .user import UserRegistrationSerializer, UserSerializer
from .produto import (
    ProdutoAlterarPrecoSerializer,
    ProdutoListSerializer,
    ProdutoRetrieveSerializer,
    ProdutoSerializer,
    ProdutoMaisVendidoSerializer,
    ProdutoAjustarEstoqueSerializer,
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
