# gui-crud-python-completo-tkinter
Interface gráfica completa de um Sistema de Cadastro, Atualização, Listagem e Remoção (CRUD) de dados de formulário sobre prestação de serviço.
Foi construído simulando um sistema de Gestão Municipal de Abastecimento de Água.
O banco de dados do sistema fica localizado na pasta `database/database.db`.
O Sistema registra logs de cada operação realizada (útil para auditorias) e faz backups automáticos do database e destes logs a cada operação de CRUD. Ambos são salvos na pasta `backups/`.
O Sistema possui opções para exportar os dados como um Excel (xlsx) que pode ser utilizado em outras ferramentas e uma opção para exportar um relatório PDF com as informações cadastradas agregadas.

# Estrutura do Sistema
./
│
├── dist/app.exe
├── app.py
├── requirements.txt
│
├── backups/
│
└── database/
    ├── database.db

# Pacotes necessários
- pandas==2.1.4 (para manipulação dos dados)
- openpyxl==3.1.2 (para geração do Excel xlsx)
- reportlab==4.0.7 (para geração do PDF)
- pyinstaller (para gerar executável .exe no Windows)
- tkinter (para construção da interface gráfica [nativo no Python])

## Instalação
```bash
pip install -r requirements.txt
# pyinstaller openpyxl reportlab
```

# Gerar executável
```bash
# Primeiro instale as dependencias
# Agora crie o executável
pyinstaller --onefile --windowed app.py
```

O executável `.exe` será salvo em: `dist/app.exe`
	
