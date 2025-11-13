import tkinter as tk
from tkinter import scrolledtext, messagebox
import google.generativeai as genai
import pyttsx3
import threading
import json
import os

# -----------------------------------------------------------------
# 1. CONFIGURAÇÃO DA API GEMINI (COM AUTO-DETECÇÃO)
# -----------------------------------------------------------------
API_KEY = "" # Mantenha sua chave real aqui

if "COLE_SUA_API_KEY" in API_KEY:
    messagebox.showerror("Erro de Configuração", 
                         "API Key não encontrada. Edite o arquivo e cole sua chave.")
    exit()

try:
    genai.configure(api_key=API_KEY)
    
    # print("Buscando modelos disponíveis para sua chave...")
    # # --- LÓGICA DE AUTO-DETECÇÃO ---
    # available_models = []
    # for m in genai.list_models():
    #     if 'generateContent' in m.supported_generation_methods:
    #         available_models.append(m.name)
    
    # for m in available_models:
    #     print(f"- {m}")
    
    # chosen_model = next((m for m in available_models if '1.5-flash' in m), None)
    # if not chosen_model:
    #     chosen_model = next((m for m in available_models if '1.5-pro' in m), None)
    # if not chosen_model:
    #     chosen_model = next((m for m in available_models if 'gemini-pro' in m), None)
    # if not chosen_model and available_models:
    #     chosen_model = available_models[0]
        
    # if not chosen_model:
    #     raise Exception("Nenhum modelo compatível encontrado para esta API Key.")

    # print(f"Modelo selecionado automaticamente: {chosen_model}")
    model = genai.GenerativeModel('models/gemini-2.0-flash')

except Exception as e:
    messagebox.showerror("Erro de API", f"Erro ao configurar Gemini:\n{e}")
    exit()

# -----------------------------------------------------------------
# 2. CARREGAMENTO DOS DADOS (MODIFICADO PARA SER MAIS LEVE)
# -----------------------------------------------------------------
def load_all_data():
    """Carrega apenas os arquivos da temporada atual (2025-26)"""
    print("Carregando arquivos JSON (Apenas temporada atual)...")
    all_data = {}
    
    # ATENÇÃO: Removemos o arquivo 'nba_espn_standings_all_seasons.json'
    # Esta é a principal causa do esgotamento da sua cota.
    filenames = [
        'nba_stats_2025_26_players_filtrado.json',
        'nba_2026_schedule_completo.json'
    ]
    
    missing_files = []
    for filename in filenames:
        if not os.path.exists(filename):
            print(f"AVISO: O arquivo {filename} não foi encontrado.")
            missing_files.append(filename)
            all_data[filename] = None
        else:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    all_data[filename] = json.load(f)
            except Exception as e:
                print(f"Erro ao carregar {filename}: {e}")

    if missing_files:
        messagebox.showwarning("Arquivos Não Encontrados",
                               f"Os seguintes arquivos não foram encontrados:\n\n"
                               f"{', '.join(missing_files)}\n\n"
                               "A IA responderá sem esses dados.")
    
    print("Dados da temporada atual carregados.")
    return json.dumps(all_data, indent=2, ensure_ascii=False)

CONTEXT_DATA = load_all_data()

# -----------------------------------------------------------------
# 3. TTS (TEXT-TO-SPEECH)
# (Esta seção permanece idêntica)
# -----------------------------------------------------------------
def speak_text(text_to_speak):
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        for v in voices:
            if 'brazil' in v.name.lower() or 'portuguese' in v.name.lower():
                engine.setProperty('voice', v.id)
                break
        engine.say(text_to_speak)
        engine.runAndWait()
    except Exception as e:
        print(f"Erro no áudio: {e}")

# -----------------------------------------------------------------
# 4. CONSULTA À IA (PROMPT ATUALIZADO)
# -----------------------------------------------------------------
def get_gemini_response(question, context):
    """Envia a pergunta e o contexto para a API Gemini."""
    
    # O prompt foi atualizado para refletir que só temos dados de 2025-26
    prompt = f"""
    Você é um assistente especialista em estatísticas da NBA.
    Sua única fonte de conhecimento são os dados JSON da temporada 2025-26 fornecidos abaixo.
    Responda à pergunta do usuário baseando-se **exclusivamente** nesses dados.
    
    Se o usuário perguntar sobre outras temporadas (ex: "quem ganhou em 2020?"),
    responda: "Eu só tenho acesso aos dados da temporada 2025-26."

    ### DADOS JSON (Temporada 2025-26) ###
    {context}
    ### FIM DADOS ###

    Pergunta do Usuário: {question}

    Resposta:
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # Se o erro 429 ocorrer mesmo assim, ele será capturado aqui
        print(f"Erro na API Gemini: {e}")
        return f"Erro na requisição: {e}"

# -----------------------------------------------------------------
# 5. INTERFACE GRÁFICA (LÓGICA DO BOTÃO ATUALIZADA)
# -----------------------------------------------------------------
def process_request():
    q = user_input.get()
    if not q: return
    
    btn_submit.config(state=tk.DISABLED, text="Pesquisando...")
    txt_output.delete("1.0", tk.END)
    txt_output.insert(tk.END, "Consultando o Gemini...")
    
    try:
        ans = get_gemini_response(q, CONTEXT_DATA)
        
        txt_output.delete("1.0", tk.END)
        txt_output.insert(tk.END, ans)
        
        # --- (MUDANÇA APLICADA AQUI) ---
        # Verifica se a caixa "Mudo" NÃO está marcada antes de falar
        if not is_muted.get():
            status_label.config(text="Falando a resposta...")
            # Thread separada para o áudio não travar a tela
            threading.Thread(target=speak_text, args=(ans,), daemon=True).start()
        else:
            status_label.config(text="Pronto (Mudo).")
        
    except Exception as e:
        txt_output.insert(tk.END, f"\nErro: {e}")
    finally:
        # Só atualiza o status se não estiver falando
        if is_muted.get():
            status_label.config(text="Pronto (Mudo).")
        else:
            # Se estiver falando, o status já foi atualizado para "Falando..."
             status_label.config(text="Pronto.") 
             
        btn_submit.config(state=tk.NORMAL, text="Perguntar")

def on_enter(event):
    threading.Thread(target=process_request, daemon=True).start()

# -----------------------------------------------------------------
# 6. CONFIGURAÇÃO DA INTERFACE GRÁFICA (ATUALIZADA)
# -----------------------------------------------------------------
root = tk.Tk()
root.title("NBA Stats Assistant")
root.geometry("700x500") # Aumentei um pouco a largura para o botão de mudo

# --- (NOVA VARIÁVEL DE ESTADO) ---
is_muted = tk.BooleanVar(value=False) # Começa desmarcado (som ativo)

main_frame = tk.Frame(root, padx=10, pady=10)
main_frame.pack(fill=tk.BOTH, expand=True)

# Frame da pergunta
input_frame = tk.Frame(main_frame)
input_frame.pack(fill=tk.X, pady=(0, 10))

tk.Label(input_frame, text="Pergunte sobre a NBA 2025-26:").pack(anchor="w")
user_input = tk.Entry(input_frame, font=("Arial", 12))
user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=5, ipady=4)
user_input.bind("<Return>", on_enter)

btn_submit = tk.Button(input_frame, text="Perguntar", command=lambda: on_enter(None), bg="#006BB6", fg="white", width=12)
btn_submit.pack(side=tk.LEFT, padx=(10, 5))

# --- (NOVO BOTÃO DE MUDO) ---
chk_mute = tk.Checkbutton(input_frame, text="Mudo", variable=is_muted)
chk_mute.pack(side=tk.LEFT, padx=5)

frame_bottom = tk.Frame(root, padx=10, pady=10)
frame_bottom.pack(fill=tk.BOTH, expand=True)

txt_output = scrolledtext.ScrolledText(frame_bottom, font=("Arial", 11), height=15)
txt_output.pack(fill=tk.BOTH, expand=True)

# Barra de Status
status_label = tk.Label(root, text="Pronto.", bd=1, relief=tk.SUNKEN, anchor="w", padx=5)
status_label.pack(side=tk.BOTTOM, fill=tk.X)

# Inicia
root.mainloop()