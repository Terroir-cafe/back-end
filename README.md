# Template de projeto Django com DRF e PDM

Esse é um template de projeto Django com DRF, PDM e muito mais. Ele já vem com algumas configurações e pacotes pré-instalados, como o PDM, Django, Django REST Framework, PostgreSQL, SQLite, Swagger, black, isort, Render, Cloudinary, Corsheaders, Django-Extensions, Django-Filter, dotenv, dj-database-url, drf-spectacular, gunicorn, netifaces, rest-framework-simplejwt, whitenoise e passage.id

Esse template já está pronto para ser utilizado em produção, com o [Render](http://render.com) e o [PostgreSQL](https://www.postgresql.org/). Mas também pode ser utilizado em desenvolvimento, com o [PDM](https://pdm.fming.dev/) e o [SQLite](https://www.sqlite.org/index.html).

O template também já vem com alguns arquivos de configuração pré-configurados, como:

- `pyproject.toml`: Arquivo de configuração do PDM.
- `Procfile`: Arquivo de configuração do Fl0.
- `settings.py`: Arquivo de configuração do Django.
- `urls.py`: Arquivo de configuração das rotas do Django.
- `wsgi.py`: Arquivo de configuração do Gunicorn.
- `.env.exemplo`: Arquivo de exemplo de configuração das variáveis de ambiente.
- `.gitignore`: Arquivo de configuração do Git, para ignorar arquivos e diretórios.

O template também traz o usuário padrão modificado, com o login sendo feito com o `e-mail` e não com o `username`. Inclusões de campos, como `telefone`, `data de nascimento` e `foto de perfil`, podem ser feitas facilmente.

O projeto Django criado chama-se `app` e a aplicação Django criada chama-se `core`. O projeto já vem com um modelo de usuário customizado, com autenticação pelo `passage.id`. Arquivos estáticos, como fotos, podem ser armazenados no [Cloudinary](https://cloudinary.com/).

O projeto também já vem com a documentação da API, gerada automaticamente pelo Swagger, e com a formatação de código Python, feita pelo black e pelo isort.

## Instalação e Configuração

1. Certifique-se de ter o [Python](https://www.python.org/) instalado em seu sistema.

2. Crie um novo projeto a partir desse template:
- Acesse o _template_ em https://github.com/marrcandre/template_django_pdm.
- Clique no botão `Use this template` em `Create a new repository`.
- Preencha as informações solicitadas:
  - `Owner`: <seu usuário no GitHub>
  - `Repository name`: `livraria`
- Click no botão `Create repository`.

3. Abra o projeto no vscode e execute o terminal.

2. Crie um ambiente virtual usando o [PDM](https://pdm.fming.dev/):

   ```
   pdm install
   ```

3. Crie o arquivo .env, a partir do arquivo .env.exemplo, e configure as variáveis de ambiente:

   ```
   cp .env.exemplo .env
   ```

4. Execute o servidor de desenvolvimento:

   ```
   pdm run dev
   ```

5. Acesse a API em http://localhost:19003/api/

## Uso da API

A documentação completa dos endpoints da API e exemplos de uso estão disponíveis na [Documentação da API](http://localhost:19003/api/swagger/).

## Comandos Úteis

- `pdm run dev`: Executa o servidor de desenvolvimento. Antes de executar o servidor, descobre o endereço IP da máquina e atualiza o arquivo `.env` com o endereço IP.
- `pdm run migrate`: Executa as migrações do banco de dados. Antes de executar o `migrate`, executa o `makemigrations`. Depois de executar o `migrate`, executa o `graph_models`, atualizando o diagrama de classes dos modelos do projeto.
- Para mais detalhes, consulte o arquivo `pyproject.toml`, na seção `[tool.pdm.scripts]`.

## Detalhes do Projeto

Esse projeto utiliza os seguintes pacotes e tecnologias:

- [PDM](https://pdm.fming.dev/): Gerenciador de pacotes e ambiente virtual para Python.
- [Django](https://www.djangoproject.com/): Framework web de alto nível escrito em Python.
- [Django REST Framework](https://www.django-rest-framework.org/): Framework para desenvolvimento de APIs REST com Django.
- [PostgreSQL](https://www.postgresql.org/): Banco de dados relacional, utilizado no ambiente de produção.
- [SQLite](https://www.sqlite.org/index.html): Banco de dados relacional, utilizado no ambiente de desenvolvimento.
- [Swagger](https://swagger.io/): Framework para documentação de APIs REST.
- [Ruff] (http://https://docs.astral.sh/ruff/): Linter e formatador de código Python, escrito em Rust.
- [Render](http://render.com): Ferramenta de _deploy_ de aplicações _backend_.
- [Cloudinary](https://cloudinary.com/): Serviço de armazenamento de arquivos estáticos em nuvem.
- [Corsheaders](https://pypi.org/project/django-cors-headers/): Pacote para permitir que aplicações frontend acessem a API.
- [Django-Extensions](https://django-extensions.readthedocs.io/en/latest/): Pacote com extensões para o Django, como o `shell_plus`, que permite acessar o shell do Django com todos os modelos importados e o comando `graph_models`, que gera um diagrama de classes dos modelos do projeto.
- [Django-Filter](https://django-filter.readthedocs.io/en/stable/): Pacote para filtragem, ordenação e paginação de dados em APIs REST.
- [dotenv](https://pypi.org/project/python-dotenv/): Pacote para carregar variáveis de ambiente a partir de um arquivo `.env`.
- [dj-database-url](https://pypi.org/project/dj-database-url/): Pacote para configurar o banco de dados a partir de uma URL.
- [drf-spectacular](https://drf-spectacular.readthedocs.io/en/latest/): Pacote para geração de documentação de APIs REST com o Swagger.
- [gunicorn](https://gunicorn.org/): Pacote para servir aplicações Django em produção.
- [netifaces](https://pypi.org/project/netifaces/): Pacote para obter o endereço IP da máquina.
- [rest-framework-simplejwt](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/): Pacote para autenticação JWT em APIs REST.
- [whitenoise](http://whitenoise.evans.io/en/stable/): Pacote para servir arquivos estáticos em aplicações Django.
- [passage.id](https://passage.id): Pacote para autenticação de usuários.

## Licença

Este projeto está licenciado sob a [Licença GPL](https://www.gnu.org/licenses/gpl-3.0.html), uma licença de software livre.




## Notificações Web Push

Os usuários podem ativar ou desativar os alertas em **Notificações → Alertas
neste dispositivo**. O recurso requer que o site e a API sejam servidos por
HTTPS em produção. Na compilação da interface, aponte `VITE_API_BASE_URL`
para a URL HTTPS da API, incluindo `/api/`. No iPhone e no iPad, adicione o site à Tela de Início e abra
o aplicativo pelo ícone para ativar os alertas.

1. Com o ambiente do Django ativado, instale a dependência do worker com
   `python -m pip install -r requirements-push.txt`. O script `build.sh`
   já inclui essa instalação.
2. Gere um par de chaves VAPID com `vapid --gen` e use
   `vapid --applicationServerKey` para obter a chave pública. Configure as
   seguintes variáveis no servidor web e no worker:
   - `WEB_PUSH_PUBLIC_KEY` com a chave pública codificada para o navegador.
   - `WEB_PUSH_PRIVATE_KEY` com o caminho do arquivo PEM privado ou com a
     chave privada DER codificada em base64. Mantenha essa chave no servidor.
   - `WEB_PUSH_SUBJECT` com o contato do operador, por exemplo
     `mailto:contato@exemplo.com`.
3. Rode `python manage.py migrate` e mantenha
   `python manage.py enviar_push --continuo` em execução em um processo
   separado. O tipo de processo `push` do Procfile executa esse comando.
   Sem `--continuo`, o comando executa um lote e encerra, para uso em
   tarefas agendadas.

O push usa mensagens genéricas na tela bloqueada e abre a central de
notificações para mostrar os detalhes após a autenticação. O worker
descarta assinaturas expiradas e repete falhas temporárias de envio.
O histórico e o estado de leitura ficam na conta mesmo com os alertas
desativados. Ao sair da conta, o navegador cancela a assinatura. Ao
entrar novamente, os alertas são retomados se já estavam ativados para
aquela conta no dispositivo e o navegador ainda permite notificações.
