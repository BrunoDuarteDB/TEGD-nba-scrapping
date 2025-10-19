import json
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 1. Configurações
URL = "https://www.nba.com/stats/players/traditional?Season=2024-25&SeasonType=Regular%20Season"
JSON_FILENAME = "nba_stats_2024_25_players_filtrado.json"

# Configuração do WebDriver
service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
# options.add_argument('--headless') # Descomente para rodar sem abrir a interface gráfica
# options.add_argument('--no-sandbox')
# options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(service=service, options=options)

print(f"Acessando o endpoint: {URL}")
all_records_df = pd.DataFrame() 

try:
    driver.get(URL)
    
    # 2. Tratamento de Cookies (Usando o ID onetrust-accept-btn-handler)
    cookie_button_id = "onetrust-accept-btn-handler"
    print("Tentando aceitar cookies...")
    try:
        cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, cookie_button_id))
        )
        cookie_button.click()
        print("Cookies aceitos com sucesso (clique por ID).")
        time.sleep(1) 
    except TimeoutException:
        print("Botão de cookies (onetrust-accept-btn-handler) não encontrado/clicável. Continuando...")
    
    
    # 3. Esperar o carregamento inicial da tabela e selecionar 'All' para a paginação
    pagination_dropdown_selector = "div.Pagination_content__f2at7 select"
    
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, pagination_dropdown_selector))
    )
    
    print("Dropdown de paginação encontrado. Tentando selecionar 'All'...")
    
    try:
        select_element = driver.find_element(By.CSS_SELECTOR, pagination_dropdown_selector)
        select = Select(select_element)
        select.select_by_value("-1") # O valor para 'All' é -1
        print("Opção 'All' selecionada. Aguardando o carregamento de todos os registros...")
        
        # Espera que a tabela seja totalmente recarregada após selecionar 'All'.
        time.sleep(5) 

    except Exception as e:
        print(f"Erro ao interagir com o dropdown: {e}. Prosseguindo com a primeira página.")


    # 4. Extrair a Tabela com Pandas
    table_css_selector = "table.Crom_table__p1iZz" 

    table_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, table_css_selector))
    )
    
    html_content = table_element.get_attribute('outerHTML')
    tables = pd.read_html(html_content)
    
    if tables:
        df = tables[0] 
        all_records_df = pd.concat([all_records_df, df], ignore_index=True)
        
        print(f"Dados brutos extraídos. Total de linhas: {len(all_records_df)}")
        
        # 5. Limpeza, Filtragem e Exportação

        # 5.1. Renomear e limpar colunas de Rank (se existir) - responsáveis por ordenação visual
        if 'Unnamed: 0' in all_records_df.columns:
            all_records_df = all_records_df.rename(columns={'Unnamed: 0': 'RANK'})
        
        # 5.2. FILTRAGEM CRUCIAL: Remove todas as colunas que terminam com 'RANK'
        cols_to_keep = [col for col in all_records_df.columns 
                        if not str(col).strip().endswith(' RANK')]
        
        # Seleciona apenas as colunas que queremos manter
        df_final = all_records_df[cols_to_keep]

        # 5.3. Remover linhas nulas, se houver
        df_final = df_final.dropna(how='all')

        # 5.4. Converte o DataFrame final para JSON
        data_json = df_final.to_json(orient='records', indent=4)
        
        with open(JSON_FILENAME, 'w', encoding='utf-8') as f:
            f.write(data_json)
        
        print(f"\n--- SUCESSO ---")
        print(f"Dados exportados para o arquivo: {JSON_FILENAME}")
        print(f"Total de registros exportados (após limpeza): {len(df_final)}")
        
    else:
        print("Nenhuma tabela HTML encontrada na página após o carregamento.")

except Exception as e:
    print(f"\n--- ERRO CRÍTICO DURANTE O SCRAPING ---")
    print(f"Ocorreu um erro: {e}")

finally:
    # 6. Fechar o navegador
    driver.quit()
    print("\nNavegador fechado. Script finalizado.")