import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import pandas as pd
from datetime import datetime
import pytz
import re
import os

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib import colors
from reportlab.platypus import TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter

# Requer instalação: pip install tkcalendar
from tkcalendar import DateEntry

if not os.path.exists("database"):
    os.mkdir("database")

DB = "database/database.db"

CAMPOS = [
    "nome", "apelido", "cpf", "endereco", "ponto_referencia",
    "localidade", "contato", "data_pedido", "data_recebimento",
    "observacoes"
]

DIC_CAMPOS = {
    "endereco": "Endereço", "ponto_referencia": "Ponto de Referência",
    "observacoes": "Observações", 
}

# =========================
# BANCO SQLITE
# =========================

def conectar():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        NM_ACAO TEXT,
        NM_USUARIO TEXT,
        _DT_CRIACAO TEXT
    )
    """)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS pessoas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {", ".join([f"{c} TEXT" for c in CAMPOS])},
            _DT_CRIACAO TEXT,
            _DT_ATUALIZACAO TEXT
        )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        NM_ACAO TEXT,
        NM_USUARIO TEXT,
        _DT_CRIACAO TEXT
    )
    """)

    conn.commit()
    return conn

# =========================
# APP
# =========================

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("[GUI] CRUD Completo Python com tkinter")
        self.root.geometry("1200x650")

        self.conn = conectar()
        self.entries = {}
        self.vars = {} # Armazena as variáveis para as máscaras
        
        self.criar_interface()
        self.listar()

    def __now(self):
        return datetime.now(tz=pytz.timezone("America/Sao_Paulo"))

    def log(self, acao):
        conn = conectar()
        conn.execute(
            "INSERT INTO auditoria (NM_ACAO, NM_USUARIO, _DT_CRIACAO) VALUES (?, ?, ?)",
            (acao, "admin", f"{self.__now()}")
        )
        conn.commit()
    
    def backup(self):
        if not os.path.exists("backups"):
            os.mkdir("backups")
        # Backup dos Daos
        nome = f"backups/backup_db_{self.__now().strftime('%Y%m%d%H')}.db"
        with open(DB, 'rb') as original:
            with open(nome, 'wb') as copia:
                copia.write(original.read())
        
        # Backup dos Logs
        bkp_logs = f"backups/backup_logs.xlsx"
        # conn = conectar()
        pd.read_sql_query(
            f"SELECT * FROM auditoria ORDER BY CAST(_DT_CRIACAO AS TIMESTAMP) DESC",
            self.conn
        ).to_excel(bkp_logs, index=False)
        # conn.close() # Fecha a conexão

    def criar_interface(self):
        # --- ÁREA DE INPUT ---
        frame_input = tk.LabelFrame(self.root, text=" Formulário ", padx=10, pady=10)
        frame_input.pack(pady=10, fill="x", padx=10)

        for i, campo in enumerate(CAMPOS):
            row, col = i // 3, (i % 3) * 2
            tk.Label(frame_input, text=(DIC_CAMPOS.get(campo, campo)).replace("_", " ").title() if campo.lower() != 'cpf' else 'CPF' + ":").grid(row=row, column=col, sticky="e", pady=5)
            
            if "data" in campo and campo:
                # Calendário
                ent = DateEntry(frame_input, width=22, background='darkblue',
                                foreground='white', borderwidth=2, locale='pt_BR', date_pattern='dd/mm/yyyy')
                if campo in ["data_recebimento"]:
                    ent.delete(0, "end")
                self.entries[campo] = ent
            else:
                # Entry com Máscara
                var = tk.StringVar()
                if campo == "observacoes":
                    ent = tk.Entry(frame_input, width=35, textvariable=var)
                else:
                    ent = tk.Entry(frame_input, width=25, textvariable=var)
                
                # if campo == "cpf":
                #     var.trace_add("write", lambda *args: self.mascara_cpf(var))
                # elif campo == "contato":
                #     var.trace_add("write", lambda *args: self.mascara_contato(var))
                
                self.entries[campo] = ent
                self.vars[campo] = var
            
            ent.grid(row=row, column=col+1, padx=5, pady=5)

        # --- BARRA DE BOTÕES ---
        botoes_frame = tk.Frame(self.root)
        botoes_frame.pack(pady=10)

        # Estilização dos botões
        estilo_btn = {"width": 12, "pady": 5}

        tk.Button(botoes_frame, text="Adicionar", command=self.adicionar, bg="#2ecc71", fg="white", **estilo_btn).grid(row=0, column=0, padx=5)
        tk.Button(botoes_frame, text="Atualizar", command=self.atualizar, bg="#f1c40f", **estilo_btn).grid(row=0, column=1, padx=5)
        tk.Button(botoes_frame, text="Limpar Campos", command=self.limpar_campos, bg="#95a5a6", fg="white", **estilo_btn).grid(row=0, column=2, padx=5)
        tk.Button(botoes_frame, text="Excluir", command=self.excluir, bg="#e74c3c", fg="white", **estilo_btn).grid(row=0, column=3, padx=5)
        tk.Button(botoes_frame, text="Exportar Excel", command=self.gerar_dados_excel, bg="#00523e", fg="white", **estilo_btn).grid(row=0, column=4, padx=5)
        tk.Button(botoes_frame, text="Relatório PDF", command=self.relatorio_pdf, bg="#2e31e2", fg="white", **estilo_btn).grid(row=0, column=5, padx=5)
        tk.Button(botoes_frame, text="Importar Dados", command=self.import_file, bg="#88006d", fg="white", **estilo_btn).grid(row=0, column=6, padx=5)

        # --- BUSCA ---
        busca_frame = tk.Frame(self.root)
        busca_frame.pack(pady=5)
        
        tk.Label(busca_frame, text="Pesquisar Nome:").pack(side="left", padx=5)
        self.busca_entry = tk.Entry(busca_frame, width=30)
        self.busca_entry.pack(side="left", padx=5)
        tk.Button(busca_frame, text="Buscar (nome ou CPF)", command=self.buscar).pack(side="left")

        # --- TABELA (TREEVIEW) ---
        self.tree = ttk.Treeview(self.root, columns=CAMPOS, show="headings")
        for c in CAMPOS:
            self.tree.heading(c, text=c.replace("_", " ").upper())
            self.tree.column(c, width=120)
        
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.selecionar)

    # =========================
    # LÓGICA DE MÁSCARAS
    # =========================

    # def mascara_cpf(self, var):
    #     v = re.sub(r'\D', '', var.get())[:11]
    #     res = ""
    #     for i, char in enumerate(v):
    #         if i == 3 or i == 6: res += "."
    #         elif i == 9: res += "-"
    #         res += char
    #     var.set(res)

    # def mascara_contato(self, var):
    #     v = re.sub(r'\D', '', var.get())[:11]
    #     res = ""
    #     if len(v) > 0:
    #         res = "(" + v[:2]
    #         if len(v) > 2:
    #             res += ") " + v[2:7]
    #             if len(v) > 7:
    #                 res += "-" + v[7:]
    #     var.set(res)

    # =========================
    # FUNÇÕES DE APOIO
    # =========================

    def limpar_campos(self):
        """Reseta todos os widgets de entrada"""
        for campo in CAMPOS:
            if "data" in campo:
                if campo in ["data_recebimento"]:
                    self.entries[campo].delete(0, "end")
                else:
                    self.entries[campo].set_date(self.__now())
            else:
                self.vars[campo].set("")
        self.tree.selection_remove(self.tree.selection()) # Remove seleção da tabela

    def selecionar(self, event):
        item = self.tree.selection()
        if item:
            valores = self.tree.item(item[0])["values"]
            for i, c in enumerate(CAMPOS):
                if "data" in c:
                    try:
                        self.entries[c].set_date(datetime.strptime(str(valores[i]), "%d/%m/%Y"))
                    except: pass
                else:
                    self.vars[c].set(valores[i])

    # =========================
    # CRUD
    # =========================

    def adicionar(self):
        # Validação simples
        if len(self.vars["nome"].get()) < 3:
            messagebox.showwarning("Aviso", "Por favor, digite o nome completo.")
            return
        elif len(self.vars["cpf"].get()) != 11 or re.search(r'[^0-9]', self.vars["cpf"].get()):
            messagebox.showerror("Erro", "CPF Inválido. Necessário ter 11 dígitos e apenas números!")
            return
        elif self.vars.get("data_recebimento") and self.vars["data_pedido"].get() > self.vars["data_recebimento"].get():
            messagebox.showerror("Erro", "Data de recebimento não pode ser anterior à data do pedido.")
            return
        elif len(self.vars["contato"].get()) != 11 or re.search(r'[^0-9]', self.vars["contato"].get()):
            messagebox.showerror("Erro", "Contato Inválido. Necessário ter 11 dígitos e apenas números. Exemplo: 74988887777")
            return

        dados = [self.entries[c].get() for c in CAMPOS] + [f"{self.__now()}", f"{self.__now()}"]
        self.conn.execute(f"INSERT INTO pessoas ({','.join(CAMPOS + ['_DT_CRIACAO', '_DT_ATUALIZACAO'])}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", dados)
        self.conn.commit()
        self.listar()
        self.log(f"Novo cadastro realizado: {self.entries['cpf'].get()}")
        self.backup()
        self.limpar_campos()
        messagebox.showinfo("Sucesso", "Registo adicionado!")

    def atualizar(self):
        item = self.tree.selection()
        if not item: 
            messagebox.showwarning("Aviso", "Selecione um registo na tabela primeiro.")
            return
            
        id_reg = self.tree.item(item[0])["text"]
        dados = [self.entries[c].get() for c in CAMPOS]
        
        self.conn.execute(
            f"""UPDATE pessoas SET 
                nome=?, apelido=?, cpf=?, endereco=?, ponto_referencia=?,
                localidade=?, contato=?, data_pedido=?, data_recebimento=?,
                observacoes=?, _DT_ATUALIZACAO=?
                WHERE id=?
            """,
            dados + [f"{self.__now()}"] + [id_reg]
        )
        
        self.conn.commit()
        self.listar()
        messagebox.showinfo("Sucesso", "Dados atualizados!")

        self.log(f"Registro atualizado: {self.entries['cpf'].get()}")
        self.backup()

    def excluir(self):
        item = self.tree.selection()
        if not item: return
        
        if messagebox.askyesno("Confirmar", "Tem a certeza que deseja eliminar?"):
            cpfs_removidos = []
            for i in item:
                cpfs_removidos.append(pd.read_sql(f"SELECT DISTINCT cpf FROM pessoas WHERE id={self.tree.item(i)['text']}", self.conn)['cpf'].iloc[0])
                self.conn.execute("DELETE FROM pessoas WHERE id=?", (self.tree.item(i)["text"],))
            self.conn.commit()
            self.listar()
            self.limpar_campos()

            self.log(f"CPFs removidos: {', '.join(cpfs_removidos)}")
            self.backup()

    def listar(self):
        self.tree.delete(*self.tree.get_children())
        for row in self.conn.execute("SELECT * FROM pessoas"):
            self.tree.insert("", "end", text=row[0], values=row[1:])

    def buscar(self):
        termo = self.busca_entry.get()
        self.tree.delete(*self.tree.get_children())
        for row in self.conn.execute("SELECT * FROM pessoas WHERE LOWER(nome) LIKE ? OR cpf LIKE ?", ('%'+termo.lower()+'%', '%'+termo.lower()+'%', )):
            self.tree.insert("", "end", text=row[0], values=row[1:])

    def gerar_dados_excel(self):
        try:
            df = pd.read_sql_query("SELECT * FROM pessoas", self.conn)
            filename = f"Planilha.xlsx" # f"planilha_{self.__now().strftime('%d%m%Y_%H%M')}.xlsx"
            df.to_excel(filename, index=False)
            messagebox.showinfo("Relatório", f"Exportado com sucesso: {filename}")

            self.log(f"Relatório Excel exportado: {filename}")            
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar excel: {e}")

    def relatorio_pdf(self):
        # conn = conectar()
        df = pd.read_sql_query(f"""
            SELECT
                SUBSTRING(data_pedido, 4, 10) AS `Mês do Pedido`,
                localidade AS Localidade,
                CASE WHEN COALESCE(data_recebimento, '') = '' THEN 'PENDENTE' ELSE 'ENTREGUE' END AS Status,
                COUNT(*) AS Quantidade,
                AVG(
                    CASE
                        WHEN data_recebimento IS NOT NULL AND data_recebimento <> ''
                        THEN julianday(CAST(data_recebimento AS DATE)) - julianday(CAST(data_pedido AS DATE))
                        ELSE NULL
                    END
                ) AS `Média de dias até o recebimento`
            FROM pessoas
            GROUP BY SUBSTRING(data_pedido, 4, 10), localidade, CASE WHEN data_recebimento IS NULL THEN 'PENDENTE' ELSE 'ENTREGUE' END
            ORDER BY data_pedido DESC, Localidade, Status
            """,
            self.conn
        )
        df = pd.concat([df, pd.DataFrame({
            "Mês do Pedido": ["-"],
            "Localidade": ["TODAS"],
            "Status": ["-"],
            "Quantidade": [df['Quantidade'].sum()],
            "Média de dias até o recebimento": [df['Média de dias até o recebimento'].mean()],
        })]).fillna("-")
        # conn.close() # Sempre feche a conexão

        nome_arquivo = "Relatorio.pdf"
        
        # 1. Configuração do Documento
        doc = SimpleDocTemplate(nome_arquivo, pagesize=letter)
        elements = []

        # 2. Estilização e Tabela
        tabela_dados = [df.columns.tolist()] + df.values.tolist()
        tabela = Table(tabela_dados)
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))

        # 3. Montagem do PDF
        elements.append(Paragraph(
            "[GUI] CRUD Completo Python com tkinter",
            ParagraphStyle(name='Titulo', fontSize=14, alignment=1))) # alignment 1 = Center
        elements.append(Spacer(1, 0.5 * inch))

        elements.append(
            Paragraph(
                "Distribuição dos dados por localidade e status de recebimento",
                ParagraphStyle(name='Descrição Tabela Localidade', alignment=1) # alignment 1 = Center
            ) # alignment 1 = Center
        )
        elements.append(tabela)

        # 4. O comando que efetivamente SALVA o arquivo no disco
        try:
            doc.build(elements)
            print(f"PDF gerado com sucesso: {nome_arquivo}")
            messagebox.showinfo("Relatório", f"PDF gerado com sucesso: {nome_arquivo}")
            # return nome_arquivo
        except Exception as e:
            print(f"Erro ao salvar PDF: {e}")
            messagebox.showerror("Erro", f"Falha ao gerar PDF: {e}")
            # return None

        self.log(f"Relatório PDF exportado: {nome_arquivo}")
    
    def import_file(self):
        """Opens a file dialog, reads the selected file into a pandas DataFrame, and prints its head."""
        # Use askopenfilename to get the full path of the selected file
        filename = filedialog.askopenfilename(
            title="Selecione um arquivo Excel para importar",
            filetypes=(
                # ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
            )
        )
        
        if filename:
            try:
                if filename.endswith('.xlsx') or filename.endswith('.xls'):
                    df = pd.read_excel(filename).assign(**{
                        "_DT_CRIACAO": f"{self.__now()}",
                        "_DT_ATUALIZACAO": f"{self.__now()}",
                    })
                else:
                    messagebox.showerror("Erro", f"Formato de arquivo `{filename.split('.')[-1]}` não suportado: {filename}")
                print(f"Successfully loaded file: {filename}")
            except Exception as e:
                print(f"Error reading file {filename}: {e}")
                tk.messagebox.showerror("Error", f"Falha ao ler o arquivo {filename}:\n{e}")
            
            colunas_ref = [x for x in pd.read_sql_query("SELECT * FROM pessoas LIMIT 1", self.conn).columns if x.lower() != 'id']
            if df.shape[0] > 0 and set(df.columns) == set(colunas_ref):
                df.to_sql("pessoas", self.conn, if_exists="append", index=False)
            else:
                tk.messagebox.showerror("Error", f"Arquivo {filename} sem dados ou com nome de colunas diferente do padrão abaixo:\n{colunas_ref}")
            # Log
            self.log(f"Importados {df.shape[0]} registros do arquivo: {filename}")

            self.listar()
            messagebox.showinfo("Sucesso", f"Importados {df.shape[0]} registros do arquivo: {filename}")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop
