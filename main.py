import json
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# --- CONFIGURAÇÕES GLOBAIS ---
# Usamos o ChromeDriverManager para instalar o driver automaticamente
SERVICE = Service(ChromeDriverManager().install())
OPTIONS = webdriver.ChromeOptions()
# OPTIONS.add_argument('--headless') # Descomente para rodar sem abrir a interface
# OPTIONS.add_argument('--no-sandbox')
# OPTIONS.add_argument('--disable-dev-shm-usage')

def setup_driver():
    """Inicializa e retorna o WebDriver."""
    return webdriver.Chrome(service=SERVICE, options=OPTIONS)


def scraper_nba_stats(driver):
    """
    Método 1: Scraper NBA Stats (com seleção 'All' e remoção de colunas RANK).
    Endpoint: https://www.nba.com/stats/players/traditional?Season=1996-97&SeasonType=Regular%20Season
    """
    URL = "https://www.nba.com/stats/players/traditional?Season=1996-97&SeasonType=Regular%20Season"
    JSON_FILENAME = "nba_stats_1996_97_players_filtrado.json"
    all_records_df = pd.DataFrame() 

    print("=" * 50)
    print("INICIANDO SCRAPER 1: NBA PLAYER STATS")
    print(f"Acessando o endpoint: {URL}")

    try:
        driver.get(URL)
        
        # 2. Tratamento de Cookies (ID: onetrust-accept-btn-handler)
        cookie_button_id = "onetrust-accept-btn-handler"
        try:
            cookie_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, cookie_button_id))
            )
            cookie_button.click()
            print("Cookies aceitos com sucesso.")
            time.sleep(1) 
        except TimeoutException:
            print("Botão de cookies não encontrado. Continuando...")
        
        
        # 3. Esperar e selecionar 'All' para a paginação
        pagination_dropdown_selector = "div.Pagination_content__f2at7 select"
        
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, pagination_dropdown_selector))
        )
        
        print("Dropdown de paginação encontrado. Tentando selecionar 'All'...")
        
        try:
            select_element = driver.find_element(By.CSS_SELECTOR, pagination_dropdown_selector)
            select = Select(select_element)
            select.select_by_value("-1") # Valor para 'All'
            print("Opção 'All' selecionada. Aguardando o carregamento de todos os registros...")
            time.sleep(5) 

        except Exception as e:
            print(f"Erro ao selecionar 'All': {e}. Prosseguindo com o que estiver carregado.")


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
            
            # 5. Limpeza e Exportação

            # 5.1. Renomear e limpar a coluna de Rank (se existir)
            if 'Unnamed: 0' in all_records_df.columns:
                all_records_df = all_records_df.rename(columns={'Unnamed: 0': 'RANK'})
            
            # 5.2. FILTRAGEM CRUCIAL: Remove colunas que terminam com 'RANK'
            cols_to_keep = [col for col in all_records_df.columns 
                            if not str(col).strip().endswith(' RANK')]
            
            df_final = all_records_df[cols_to_keep]

            # 5.3. Remover linhas nulas
            df_final = df_final.dropna(how='all')

            # 5.4. Converte e salva no JSON
            data_json = df_final.to_json(orient='records', indent=4)
            
            with open(JSON_FILENAME, 'w', encoding='utf-8') as f:
                f.write(data_json)
            
            print(f"\n--- SUCESSO SCRAPER 1 ---")
            print(f"Dados exportados para o arquivo: {JSON_FILENAME}")
            print(f"Total de registros exportados: {len(df_final)}")
            
        else:
            print("Nenhuma tabela de stats de jogadores encontrada.")

    except Exception as e:
        print(f"\n--- ERRO CRÍTICO SCRAPER 1 ---")
        print(f"Ocorreu um erro: {e}")


def scraper_basketball_reference_schedule(driver):
    """
    Método 2: Scraper Basketball-Reference Schedule (com iteração por meses).
    Endpoint: https://www.basketball-reference.com/leagues/NBA_2026_games-october.html
    """
    BASE_URL = "https://www.basketball-reference.com"
    START_URL = f"{BASE_URL}/leagues/NBA_2026_games-october.html"
    JSON_FILENAME = "nba_2026_schedule_completo.json"
    all_games_df = pd.DataFrame()
    
    print("\n\n" + "=" * 50)
    print("INICIANDO SCRAPER 2: BASKETBALL-REFERENCE SCHEDULE")
    print(f"Acessando o endpoint inicial: {START_URL}")

    try:
        driver.get(START_URL)

        # 1. Esperar pelo carregamento dos filtros de mês
        filter_div_selector = "div.filter"
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, filter_div_selector))
        )
        
        # Encontrar todos os links de meses
        month_links = driver.find_elements(By.CSS_SELECTOR, f"{filter_div_selector} a")
        
        # Criar uma lista de URLs a visitar, incluindo o mês atual
        urls_to_scrape = [driver.current_url]
        for link in month_links:
            # Garante que só peguemos links com nomes de meses e a URL completa
            if "games-" in link.get_attribute("href"):
                urls_to_scrape.append(link.get_attribute("href"))
        
        # Remove duplicatas e mantém a ordem
        urls_to_scrape = sorted(list(set(urls_to_scrape)), key=lambda x: ['october', 'november', 'december', 'january', 'february', 'march', 'april'].index(x.split('-')[-1].split('.')[0]))


        # 2. Iterar sobre cada URL de mês para extrair a tabela
        for url in urls_to_scrape:
            month_name = url.split('-')[-1].split('.')[0].capitalize()
            print(f"\n--> Coletando dados para o mês: {month_name}")

            # Navegar para o link (se não for a página atual)
            if url != driver.current_url:
                driver.get(url)
                
            # Esperar que a tabela seja recarregada
            table_css_selector = "table#schedule" # Usando o ID da tabela
            try:
                # Esperamos por 10 segundos, mas com StaleElementReferenceException handling
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, table_css_selector))
                )
                
                # Garante que o elemento está pronto antes de tentar o read_html
                table_element = driver.find_element(By.CSS_SELECTOR, table_css_selector)
                html_content = table_element.get_attribute('outerHTML')
                
                # Extrai a tabela
                tables = pd.read_html(html_content)
                
                if tables:
                    df_month = tables[0]
                    # Adiciona uma coluna para identificar o mês
                    df_month['Month'] = month_name
                    
                    all_games_df = pd.concat([all_games_df, df_month], ignore_index=True)
                    print(f"   -> {len(df_month)} jogos adicionados. Total: {len(all_games_df)}")
                
            except (TimeoutException, StaleElementReferenceException) as e:
                print(f"   -> Erro ao carregar ou processar a tabela para {month_name}: {e}")
                continue # Continua para o próximo mês

        
        # 3. Limpeza e Exportação Final
        if not all_games_df.empty:
            # Remove linhas de cabeçalho repetidas (que o read_html pode capturar)
            # A coluna 'Date' deve ter a tag <th> no cabeçalho.
            df_final = all_games_df[all_games_df['Date'] != 'Date'] 
            
            # Adiciona o prefixo 'BBR_' para as colunas de Rank que o Pandas pode ter adicionado
            if 'Unnamed: 3' in df_final.columns and 'PTS' in df_final.columns:
                 df_final = df_final.rename(columns={'Unnamed: 3': 'Visitor PTS', 'PTS': 'Home PTS'})

            # Converte e salva no JSON
            data_json = df_final.to_json(orient='records', indent=4)
            
            with open(JSON_FILENAME, 'w', encoding='utf-8') as f:
                f.write(data_json)
            
            print(f"\n--- SUCESSO SCRAPER 2 ---")
            print(f"Dados exportados para o arquivo: {JSON_FILENAME}")
            print(f"Total de jogos exportados: {len(df_final)}")

        else:
            print("Nenhum dado de agendamento foi coletado.")

    except Exception as e:
        print(f"\n--- ERRO CRÍTICO SCRAPER 2 ---")
        print(f"Ocorreu um erro: {e}")


# --- EXECUÇÃO PRINCIPAL ---

# Inicializa o driver (será usado por ambos os scrapers)
driver = setup_driver()

# Roda o primeiro scraper
scraper_nba_stats(driver)

# Roda o segundo scraper
scraper_basketball_reference_schedule(driver)

# Fecha o navegador
driver.quit()