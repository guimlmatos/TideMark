import os
import re
import json
import threading
import tempfile
import webbrowser
import customtkinter as ctk
import anthropic
from tavily import TavilyClient
from dotenv import load_dotenv

# Visualização de Gráficos e Exportação de Imagens
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Carrega variáveis do arquivo .env
load_dotenv()

# Configurações visuais do CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class CyberpunkExecutiveAgent(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configurações de Janela
        self.title("CYBER_ANALYST v5.0 // SISTEMA PROCEDURAL DE INTELIGÊNCIA DE MERCADO")
        self.geometry("1200x850")
        self.configure(fg_color="#0B0C10")  # Fundo Preto Obsidian

        # Paleta Neon Cyberpunk
        self.CYAN = "#66FCF1"
        self.DARK_CYAN = "#45A29E"
        self.GRAY = "#1F2833"
        self.WHITE = "#C5C6C7"

        self.last_report_text = ""
        self.last_market = ""
        self.last_location = ""
        self.chart_images = {}

        self.setup_ui()

    def setup_ui(self):
        # Header
        header = ctk.CTkLabel(
            self, 
            text="SYSTEM // AGENTE DE ANÁLISE DE MERCADO MULTIDIMENSIONAL", 
            font=("Consolas", 18, "bold"), 
            text_color=self.CYAN
        )
        header.pack(pady=15)

        # Frame de Entrada de Dados
        input_frame = ctk.CTkFrame(self, fg_color=self.GRAY, corner_radius=8)
        input_frame.pack(fill="x", padx=20, pady=5)

        self.market_entry = ctk.CTkEntry(
            input_frame, 
            placeholder_text="Nicho/Mercado (ex: Sensores de microclima para agronegócio)", 
            width=480, fg_color="#0B0C10", text_color="#FFFFFF"
        )
        self.market_entry.grid(row=0, column=0, padx=10, pady=10)

        self.location_entry = ctk.CTkEntry(
            input_frame, 
            placeholder_text="Região/Cidade (ex: Brasília - DF)", 
            width=300, fg_color="#0B0C10", text_color="#FFFFFF"
        )
        self.location_entry.grid(row=0, column=1, padx=10, pady=10)

        # Botão Executar
        self.btn_run = ctk.CTkButton(
            input_frame, text="INICIAR VARREDURA PROCEDURAL", 
            font=("Consolas", 12, "bold"),
            fg_color=self.DARK_CYAN, hover_color=self.CYAN, 
            text_color="#000000", command=self.start_analysis_thread
        )
        self.btn_run.grid(row=0, column=2, padx=10, pady=10)

        # Barra de Ações do Relatório
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=20, pady=5)

        self.status_label = ctk.CTkLabel(
            action_frame, text="[SYSTEM READY] // Aguardando parâmetros de entrada...", 
            font=("Consolas", 11), text_color=self.WHITE
        )
        self.status_label.pack(side="left", padx=5)

        self.btn_export_html = ctk.CTkButton(
            action_frame, text="🌐 ABRIR DOSSIÊ EXECUTIVO (NAVEGADOR)", 
            font=("Consolas", 11, "bold"),
            fg_color="#1F2833", hover_color=self.DARK_CYAN,
            text_color=self.CYAN, border_width=1, border_color=self.CYAN,
            command=self.open_formatted_html, state="disabled"
        )
        self.btn_export_html.pack(side="right", padx=5)

        self.btn_open_charts = ctk.CTkButton(
            action_frame, text="📊 DASHBOARD INTERATIVO", 
            font=("Consolas", 11, "bold"),
            fg_color="#1F2833", hover_color=self.DARK_CYAN,
            text_color=self.CYAN, border_width=1, border_color=self.CYAN,
            command=self.open_interactive_charts, state="disabled"
        )
        self.btn_open_charts.pack(side="right", padx=5)

        # Área Principal de Exibição de Texto
        text_frame = ctk.CTkFrame(self, fg_color=self.GRAY, corner_radius=8)
        text_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.report_text = ctk.CTkTextbox(
            text_frame, font=("Consolas", 13), 
            fg_color="#0B0C10", text_color=self.CYAN, wrap="word",
            activate_scrollbars=True
        )
        self.report_text.pack(fill="both", expand=True, padx=10, pady=10)

    def log(self, message):
        self.status_label.configure(text=f"[SYS_LOG] {message}")

    def update_report_display(self, text):
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", text)
        self.report_text.see("1.0")

    def append_report_display(self, text):
        self.report_text.insert("end", text + "\n\n")
        self.report_text.see("end")

    def start_analysis_thread(self):
        threading.Thread(target=self.run_analysis, daemon=True).start()

    def generate_chapter_prompt(self, chapter_num, chapter_title, questions, market, location, context):
        """Molde padronizado de instrução por capítulo"""
        q_list = "\n".join([f"- {q}" for q in questions])
        return f"""
        Você é um Consultor Sênior em Estratégia e Inteligência de Mercado.
        Gere EXCLUSIVAMENTE o **CAPÍTULO {chapter_num}: {chapter_title.upper()}** para o mercado '{market}' na região '{location}'.

        DADOS DA WEB EM TEMPO REAL:
        {context}

        INSTRUÇÕES DE RESPOSTA:
        1. Responda detalhadamente a CADA UMA das perguntas abaixo de forma profunda e exaustiva.
        2. Use formatação Markdown (subcabeçalhos ###, negritos, tópicos e tabelas onde couber).
        3. Comece o texto exatamente com '## {chapter_num}. {chapter_title.upper()}'.

        PERGUNTAS A SEREM RESPONDIDAS PROCEDURALMENTE NESTE CAPÍTULO:
        {q_list}
        """

    def run_analysis(self):
        claude_key = os.getenv("ANTHROPIC_API_KEY")
        tavily_key = os.getenv("TAVILY_API_KEY")

        market = self.market_entry.get().strip()
        location = self.location_entry.get().strip()

        if not claude_key or not market:
            self.log("ERRO: Verifique a API Key no .env e o nicho de mercado!")
            return

        self.btn_run.configure(state="disabled")
        self.btn_export_html.configure(state="disabled")
        self.btn_open_charts.configure(state="disabled")

        self.last_market = market
        self.last_location = location if location else "Brasil"
        self.update_report_display(f"[SISTEMA EM EXECUÇÃO PROCEDURAL SIMULTÂNEA]\nIniciando geração do Dossiê para '{market}' em '{self.last_location}'...\n")

        try:
            # 1. VARREDURA TAVILY
            contexto_pesquisa = ""
            if tavily_key:
                tavily = TavilyClient(api_key=tavily_key)
                queries = [
                    f"principais empresas concorrentes produtos servicos {market} {location}",
                    f"demanda mercado tiquete medio custos operacionais {market}",
                    f"editais fapdf finep sebrae incentivo financiamento {market} {location}"
                ]

                for i, q in enumerate(queries, 1):
                    self.log(f"Pesquisando Web ({i}/3): '{q[:35]}...'")
                    try:
                        res = tavily.search(query=q, max_results=3)
                        contexto_pesquisa += f"\n--- PESQUISA WEB {i}: {q} ---\n"
                        contexto_pesquisa += "\n".join([f"- {r['title']}: {r['content']}" for r in res.get('results', [])])
                    except Exception as e:
                        contexto_pesquisa += f"\n[Falha busca {i}: {e}]\n"
            else:
                self.log("Aviso: TAVILY_API_KEY ausente. Analisando via conhecimento interno...")

            client = anthropic.Anthropic(api_key=claude_key)

            # 2. ETAPA PRELIMINAR: EXTRAÇÃO DO JSON DE MÉTRICAS PARA GRÁFICOS
            self.log("Extraindo métricas numéricas para o dashboard...")
            json_prompt = f"""
            Analise o nicho '{market}' na região '{location}'.
            Retorne APENAS um bloco JSON válido no seguinte formato:
            ```json
            {{
                "tam": 50000000,
                "sam": 12000000,
                "som": 2500000,
                "receitas_5anos": [200000, 500000, 1100000, 2200000, 3800000],
                "opex_5anos": [130000, 260000, 480000, 850000, 1300000],
                "capex_categorias": ["P&D / Protótipo", "Infraestrutura", "Marketing", "Reserva Operacional"],
                "capex_valores": [45000, 25000, 15000, 30000],
                "radar_notas": [8, 9, 7, 9, 8]
            }}
            ```
            """
            json_msg = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[{"role": "user", "content": json_prompt}]
            )

            json_text_response = ""
            for block in json_msg.content:
                if getattr(block, 'type', None) == 'text':
                    json_text_response += block.text

            metrics = {
                "tam": 40000000, "sam": 10000000, "som": 2000000,
                "receitas_5anos": [180000, 420000, 900000, 1800000, 3200000],
                "opex_5anos": [110000, 220000, 420000, 750000, 1100000],
                "capex_categorias": ["P&D / Protótipo", "Infraestrutura", "Marketing", "Reserva"],
                "capex_valores": [40000, 20000, 15000, 25000],
                "radar_notas": [8, 8, 7, 9, 8]
            }

            json_match = re.search(r'```json\s*(\{.*?\})\s*```', json_text_response, re.DOTALL)
            if json_match:
                try:
                    metrics = json.loads(json_match.group(1))
                except Exception:
                    pass

            self.generate_plotly_dashboard(metrics)

            # 3. ESTRUTURA PROCEDURAL DE CAPÍTULOS E SUAS PERGUNTAS ESPECÍFICAS
            capitulos = [
                {
                    "num": 1,
                    "title": "Resumo Executivo & Tese de Investimento",
                    "questions": [
                        "Qual é a tese principal de investimento e viabilidade deste mercado na região?",
                        "Quais são as dores críticas não atendidas dos clientes locais?",
                        "Quais tendências tecnológicas ou regulatórias impulsionam essa oportunidade agora?"
                    ]
                },
                {
                    "num": 2,
                    "title": "Tamanho de Mercado & Modelagem TAM/SAM/SOM",
                    "questions": [
                        "Qual o valor estimado do TAM (Total Addressable Market) em R$ e qual a metodologia do cálculo?",
                        "Qual a fatia do SAM (Serviceable Addressable Market) na região foco?",
                        "Qual a meta realista do SOM (Serviceable Obtainable Market) nos primeiros 24 meses em R$?"
                    ]
                },
                {
                    "num": 3,
                    "title": "Panorama Competitivo & Benchmarking",
                    "questions": [
                        "Quem são os principais concorrentes diretos e indiretos operando na região?",
                        "Quais são as lacunas de atendimento deixadas pelos players atuais?",
                        "Qual é a proposta única de valor (UVP) e diferenciais técnicos recomendados?"
                    ]
                },
                {
                    "num": 4,
                    "title": "Modelo de Negócios & Precificação",
                    "questions": [
                        "Quais são as fontes de receita recomendadas (ex: SaaS, Venda Direta, Assinatura)?",
                        "Qual o tíquete médio praticável por cliente/contrato?",
                        "Qual a estratégia inicial de aquisição de clientes (CAC) e ciclo de vendas?"
                    ]
                },
                {
                    "num": 5,
                    "title": "Engenharia Financeira (CapEx, OpEx e Payback)",
                    "questions": [
                        "Qual a estimativa do CapEx inicial detalhada por categorias (máquinas, P&D, licenças)?",
                        "Qual a estimativa do OpEx mensal (equipe, infraestrutura, marketing, serviços)?",
                        "Qual o horizonte estimado para o ponto de equilíbrio (Break-even) e Payback em meses?"
                    ]
                },
                {
                    "num": 6,
                    "title": "Ecossistema de Captação & Editais de Inovação",
                    "questions": [
                        "Quais editais sem diluição (FAPDF, FINEP, SEBRAE, CNPq, Embrapii) se aplicam a este projeto?",
                        "Existem programas regionais de incentivo fiscal ou linhas de crédito bonificadas?",
                        "Qual o perfil de investidores anjo ou fundos de VC atraídos por este nicho?"
                    ]
                },
                {
                    "num": 7,
                    "title": "Análise de Riscos & Matriz SWOT",
                    "questions": [
                        "Quais são as Forças, Oportunidades, Fraquezas e Ameaças na Matriz SWOT detalhada?",
                        "Quais são os principais riscos regulatórios, operacionais e de adoção tecnológica?",
                        "Quais são os planos práticos de mitigação para cada risco mapeado?"
                    ]
                },
                {
                    "num": 8,
                    "title": "Plano de Execução Prático (30 / 90 / 180 Dias)",
                    "questions": [
                        "Quais ações devem ser executadas nos primeiros 30 dias (validação e jurídico)?",
                        "Quais marcos devem ser atingidos nos 90 dias (desenvolvimento de MVP e testes piloto)?",
                        "Quais metas comerciais e operacionais devem ser consolidadas em 180 dias?"
                    ]
                }
            ]

            full_report_text = ""

            # Execução sequencial capítulo por capítulo com auto-continuação em caso de corte
            for cap in capitulos:
                self.log(f"Gerando Capítulo {cap['num']}/8: {cap['title']}...")
                prompt_cap = self.generate_chapter_prompt(
                    cap['num'], cap['title'], cap['questions'],
                    market, self.last_location, contexto_pesquisa
                )

                messages_history = [{"role": "user", "content": prompt_cap}]
                cap_content = ""

                while True:
                    msg = client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=4000,
                        messages=messages_history
                    )

                    part_text = ""
                    for block in msg.content:
                        if getattr(block, 'type', None) == 'text':
                            part_text += block.text

                    cap_content += part_text

                    # Verifica se a resposta parou por atingir o limite de tokens
                    if msg.stop_reason == "max_tokens":
                        self.log(f"Continuando geração do Capítulo {cap['num']}...")
                        # Adiciona o histórico da conversa parcial para pedir que continue sem repetir
                        messages_history.append({"role": "assistant", "content": part_text})
                        messages_history.append({"role": "user", "content": "Continue exatamente de onde você parou, sem repetir o texto anterior."})
                    else:
                        break

                cap_content = cap_content.strip()
                full_report_text += cap_content + "\n\n"
                self.append_report_display(cap_content)

            self.last_report_text = full_report_text
            self.log("Dossiê procedural completo gerado sem interrupções!")

            self.btn_export_html.configure(state="normal")
            self.btn_open_charts.configure(state="normal")

        except Exception as e:
            err_msg = f"ERRO DE EXECUÇÃO PROCEDURAL: {str(e)}"
            self.log(err_msg)
            self.append_report_display(err_msg)

        finally:
            self.btn_run.configure(state="normal")

    def generate_plotly_dashboard(self, m):
        """Plota gráficos dinâmicos com base nos dados reais do mercado analisado"""
        temp_dir = tempfile.gettempdir()

        # 1. TAM / SAM / SOM (Pizza)
        fig1 = go.Figure(data=[go.Pie(
            labels=['TAM (Total)', 'SAM (Endereçável)', 'SOM (Objetivo)'],
            values=[m.get('tam', 0), m.get('sam', 0), m.get('som', 0)],
            hole=.4,
            marker_colors=['#45A29E', '#66FCF1', '#1F2833']
        )])
        fig1.update_layout(
            template="plotly_dark", title=f"TAM/SAM/SOM: {self.last_market}",
            paper_bgcolor="#1f2833", plot_bgcolor="#1f2833", font=dict(color="#c5c6c7")
        )
        p1 = os.path.join(temp_dir, "chart_tam.png")
        fig1.write_image(p1, width=600, height=350)
        self.chart_images['tam'] = p1

        # 2. Projeção Financeira (Barras)
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=['Ano 1', 'Ano 2', 'Ano 3', 'Ano 4', 'Ano 5'], y=m.get('receitas_5anos', []), name='Receita (R$)', marker_color='#66FCF1'))
        fig2.add_trace(go.Bar(x=['Ano 1', 'Ano 2', 'Ano 3', 'Ano 4', 'Ano 5'], y=m.get('opex_5anos', []), name='OpEx (R$)', marker_color='#FF0055'))
        fig2.update_layout(
            template="plotly_dark", title="Evolução Financeira Projetada (5 Anos)",
            paper_bgcolor="#1f2833", plot_bgcolor="#1f2833", font=dict(color="#c5c6c7")
        )
        p2 = os.path.join(temp_dir, "chart_fin.png")
        fig2.write_image(p2, width=600, height=350)
        self.chart_images['fin'] = p2

        # 3. CapEx (Barras Horizontais)
        fig3 = go.Figure(data=[go.Bar(
            y=m.get('capex_categorias', []),
            x=m.get('capex_valores', []), orientation='h', marker_color='#45A29E'
        )])
        fig3.update_layout(
            template="plotly_dark", title="Composição de CapEx Inicial (R$)",
            paper_bgcolor="#1f2833", plot_bgcolor="#1f2833", font=dict(color="#c5c6c7")
        )
        p3 = os.path.join(temp_dir, "chart_capex.png")
        fig3.write_image(p3, width=600, height=350)
        self.chart_images['capex'] = p3

        # Dashboard completo
        fig_dash = make_subplots(
            rows=2, cols=2,
            subplot_titles=("TAM / SAM / SOM", "Evolução 5 Anos (Receita vs OpEx)", "Alocação do CapEx Inicial", "Radar Competitivo"),
            specs=[[{"type": "domain"}, {"type": "xy"}], [{"type": "xy"}, {"type": "polar"}]]
        )
        fig_dash.add_trace(fig1.data[0], row=1, col=1)
        fig_dash.add_trace(fig2.data[0], row=1, col=2)
        fig_dash.add_trace(fig2.data[1], row=1, col=2)
        fig_dash.add_trace(fig3.data[0], row=2, col=1)
        fig_dash.add_trace(go.Scatterpolar(
            r=m.get('radar_notas', [8, 8, 7, 9, 8]),
            theta=['Preço', 'Inovação', 'Presença Local', 'Agilidade', 'Suporte'],
            fill='toself', line_color='#66FCF1'
        ), row=2, col=2)

        fig_dash.update_layout(
            template="plotly_dark", title_text=f"DASHBOARD TÉCNICO PROCEDURAL // {self.last_market.upper()}",
            paper_bgcolor="#0B0C10", plot_bgcolor="#0B0C10", font=dict(color="#C5C6C7")
        )

        self.dashboard_path = os.path.join(temp_dir, "cyber_dashboard.html")
        fig_dash.write_html(self.dashboard_path)

    def open_interactive_charts(self):
        if hasattr(self, 'dashboard_path') and os.path.exists(self.dashboard_path):
            webbrowser.open(f"file://{self.dashboard_path}")
        else:
            self.log("Dashboard de gráficos ainda não foi gerado.")

    def format_markdown_to_html(self, text):
        """Converte Markdown para HTML estruturado integrando as imagens de gráficos geradas"""
        lines = text.split('\n')
        html_output = []
        in_list = False

        for line in lines:
            line_str = line.strip()
            if not line_str:
                if in_list:
                    html_output.append("</ul>")
                    in_list = False
                continue

            # Formatação de Negrito (**texto**)
            line_str = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line_str)

            # Títulos de Seções (Capítulos)
            if line_str.startswith('## '):
                if in_list:
                    html_output.append("</ul>")
                    in_list = False
                title_text = line_str.replace('## ', '')
                html_output.append(f"<h2>{title_text}</h2>")

                # Insere os gráficos correspondentes
                if "TAMANHO DE MERCADO" in title_text.upper() and 'tam' in self.chart_images:
                    html_output.append(f"""
                    <div class="chart-container">
                        <img src="file://{self.chart_images['tam']}" alt="Gráfico TAM SAM SOM">
                        <div class="caption">Figura 1.1: Modelo de dimensionamento de mercado TAM, SAM e SOM em R$.</div>
                    </div>
                    """)
                elif "ENGENHARIA FINANCEIRA" in title_text.upper():
                    if 'fin' in self.chart_images:
                        html_output.append(f"""
                        <div class="chart-container">
                            <img src="file://{self.chart_images['fin']}" alt="Evolução Financeira">
                            <div class="caption">Figura 2.1: Projeção de receitas brutas acumuladas vs. custos operacionais (5 Anos).</div>
                        </div>
                        """)
                    if 'capex' in self.chart_images:
                        html_output.append(f"""
                        <div class="chart-container">
                            <img src="file://{self.chart_images['capex']}" alt="Composição CapEx">
                            <div class="caption">Figura 2.2: Alocação estratégica do investimento inicial (CapEx).</div>
                        </div>
                        """)

            # Títulos Secundários
            elif line_str.startswith('### '):
                if in_list:
                    html_output.append("</ul>")
                    in_list = False
                html_output.append(f"<h3>{line_str.replace('### ', '')}</h3>")

            # Itens de Lista
            elif line_str.startswith('- ') or line_str.startswith('* '):
                if not in_list:
                    html_output.append("<ul>")
                    in_list = True
                html_output.append(f"<li>{line_str[2:]}</li>")

            # Parágrafos
            else:
                if in_list:
                    html_output.append("</ul>")
                    in_list = False
                html_output.append(f"<p>{line_str}</p>")

        if in_list:
            html_output.append("</ul>")

        return "\n".join(html_output)

    def open_formatted_html(self):
        """Compila o Dossiê Executivo completo em HTML no estilo Dark/LaTeX"""
        if not self.last_report_text:
            return

        formatted_body = self.format_markdown_to_html(self.last_report_text)

        appendix_html = """
        <div class="appendix">
            <h2>APÊNDICE: GLOSSÁRIO DE TERMOS E JARGÕES EXECUTIVOS</h2>
            <p>Conceitos de negócios e indicadores financeiros utilizados neste relatório:</p>
            <ul>
                <li><strong>TAM (Total Addressable Market):</strong> Tamanho total do mercado se houvesse monopolização de 100% dos clientes potenciais.</li>
                <li><strong>SAM (Serviceable Addressable Market):</strong> A parcela do TAM que seu modelo de negócios e abrangência logística cobrem.</li>
                <li><strong>SOM (Serviceable Obtainable Market):</strong> Meta realista de captura de mercado nos primeiros 12 a 24 meses.</li>
                <li><strong>CapEx (Capital Expenditure):</strong> Investimento em bens duráveis (máquinas, software, patentes, estrutura inicial).</li>
                <li><strong>OpEx (Operational Expenditure):</strong> Custos mensais fixos e variáveis para manter a operação rodando.</li>
                <li><strong>Payback:</strong> Tempo em meses ou anos para que o lucro do negócio pague o CapEx inicial.</li>
                <li><strong>CAC (Custo de Aquisição de Cliente):</strong> Total gasto em marketing e vendas dividido pelo número de clientes conquistados.</li>
                <li><strong>Tíquete Médio:</strong> Valor médio gasto por cada cliente por transação ou contrato.</li>
                <li><strong>Matriz SWOT:</strong> Metodologia de avaliação das Forças, Oportunidades, Fraquezas e Ameaças do projeto.</li>
            </ul>
        </div>
        """

        html_content = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <title>Dossiê Executivo - {self.last_market}</title>
            <style>
                body {{
                    background-color: #0b0c10;
                    color: #c5c6c7;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    padding: 40px;
                    line-height: 1.7;
                }}
                .container {{
                    max-width: 950px;
                    margin: 0 auto;
                    background-color: #1f2833;
                    padding: 40px;
                    border-radius: 8px;
                    border: 1px solid #66fcf1;
                    box-shadow: 0 0 25px rgba(102, 252, 241, 0.15);
                }}
                h1 {{
                    color: #66fcf1;
                    border-bottom: 2px solid #45a29e;
                    padding-bottom: 10px;
                    font-size: 26px;
                    margin-top: 0;
                }}
                h2 {{
                    color: #66fcf1;
                    margin-top: 35px;
                    border-bottom: 1px solid #45a29e;
                    padding-bottom: 5px;
                    font-size: 18px;
                }}
                h3 {{
                    color: #45a29e;
                    font-size: 15px;
                }}
                p, li {{
                    font-size: 14px;
                    color: #d1d2d3;
                }}
                ul {{
                    padding-left: 20px;
                }}
                li {{
                    margin-bottom: 8px;
                }}
                strong {{
                    color: #ffffff;
                }}
                .meta {{
                    color: #45a29e;
                    font-weight: bold;
                    margin-bottom: 25px;
                    font-size: 13px;
                }}
                .chart-container {{
                    text-align: center;
                    margin: 25px 0;
                    background-color: #0b0c10;
                    padding: 15px;
                    border-radius: 6px;
                    border: 1px solid #45a29e;
                }}
                .chart-container img {{
                    max-width: 100%;
                    height: auto;
                    border-radius: 4px;
                }}
                .caption {{
                    font-size: 12px;
                    color: #66fcf1;
                    margin-top: 8px;
                    font-style: italic;
                }}
                .appendix {{
                    margin-top: 50px;
                    padding-top: 20px;
                    border-top: 2px dashed #45a29e;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>DOSSIÊ DE INTELIGÊNCIA DE MERCADO (PROCEDURAL)</h1>
                <div class="meta">MERCADO ANALISADO: {self.last_market.upper()} | REGIÃO ALVO: {self.last_location.upper()}</div>
                
                {formatted_body}
                {appendix_html}
            </div>
        </body>
        </html>
        """

        html_path = os.path.join(tempfile.gettempdir(), "dossie_executivo.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        webbrowser.open(f"file://{html_path}")
        self.log("Dossiê procedural exibido no navegador com sucesso!")

if __name__ == "__main__":
    app = CyberpunkExecutiveAgent()
    app.mainloop()