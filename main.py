import json
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 1. Configurações
URL = "https://www.nba.com/stats/players/traditional?Season=1996-97&SeasonType=Regular%20Season"
JSON_FILENAME = "nba_stats_1996_97_players.json"

# Configuração do WebDriver
service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
# Recomendações para produção (opcional):
# options.add_argument('--headless') # Executa em segundo plano sem abrir o navegador
# options.add_argument('--no-sandbox')
# options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(service=service, options=options)

print(f"Acessando o endpoint: {URL}")

try:
    driver.get(URL)
    
    # 2. Tratamento de Cookies
    # Usando o ID fornecido (onetrust-accept-btn-handler)
    cookie_button_id = "onetrust-accept-btn-handler"
    
    print("Tentando aceitar cookies...")
    try:
        # Espera até 10 segundos para o botão aparecer e ser clicável
        cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, cookie_button_id))
        )
        cookie_button.click()
        print("Cookies aceitos com sucesso (clique por ID).")
        time.sleep(1) # Pequena pausa para a interface se estabilizar
        
    except Exception:
        # Se o botão de cookies não for encontrado, a página provavelmente já carregou sem ele
        print("Botão de cookies não encontrado ou não clicável. Continuando o scraping...")
    
    
    # 3. Esperar o carregamento da tabela principal
    # Seletor CSS para a tabela no site da NBA
    table_selector = "div.nba-stat-table table"
    
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, table_selector))
    )
    
    print("Tabela de dados encontrada.")

    # 4. Extrair o HTML e converter para Pandas DataFrame
    
    # Obtém o HTML da página renderizado pelo Selenium
    html_content = driver.page_source
    
    # pd.read_html() extrai todas as tabelas HTML em uma lista de DataFrames
    tables = pd.read_html(html_content)
    
    if tables:
        # A tabela de jogadores geralmente é a primeira (índice 0)
        df = tables[0] 
        print(f"Dados extraídos com sucesso para um DataFrame Pandas com {len(df)} linhas.")
        
        # Opcional: Renomear a coluna de rank (que o Pandas frequentemente chama de 'Unnamed: 0')
        if 'Unnamed: 0' in df.columns:
            df = df.rename(columns={'Unnamed: 0': 'RANK'})
        
        # Opcional: Remover linhas nulas, se houver
        df = df.dropna(how='all')

        # 5. Exportar para JSON
        
        # Converte o DataFrame para uma lista de dicionários (orient='records')
        data_json = df.to_json(orient='records', indent=4)
        
        with open(JSON_FILENAME, 'w', encoding='utf-8') as f:
            f.write(data_json)
        
        print(f"\n--- SUCESSO ---")
        print(f"Dados exportados para o arquivo: {JSON_FILENAME}")
        print(f"Total de registros exportados: {len(df)}")
        
    else:
        print("Nenhuma tabela HTML encontrada na página.")

except Exception as e:
    print(f"\n--- ERRO CRÍTICO DURANTE O SCRAPING ---")
    print(f"Ocorreu um erro: {e}")

finally:
    # 6. Fechar o navegador
    driver.quit()
    print("\nNavegador fechado. Script finalizado.")